"""
app/worker.py
=============
ComputeGrid Worker – Distributed Job Consumer

Responsibility
--------------
This module is the *worker* process. Its responsibilities are:

  1. Continuously poll the Redis queue for pending job IDs.
  2. Atomically claim queued jobs in PostgreSQL (`queued` → `running`) using a
     conditional UPDATE to ensure safe multi-worker concurrency and prevent race
     conditions or duplicate job execution.
  3. Execute scientific computation workloads (e.g. NumPy matrix operations)
     asynchronously outside the API request cycle.
  4. Record computation results and timestamps in PostgreSQL upon successful completion.
  5. Handle computation errors gracefully with bounded automatic retries and re-queueing
     (up to MAX_RETRIES) before transitioning permanently to `failed`.
  6. Properly manage PostgreSQL database sessions and connection lifecycle.

How to run
----------
From the project root (with your virtual environment active):

    python -m app.worker

Multiple worker processes can be started concurrently to process jobs in parallel.
Press Ctrl+C to stop the worker.
"""

import time
import logging
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

# Reuse the existing queue abstraction.
# dequeue_job() calls LPOP on "computegrid:jobs" and returns an int or None.
# enqueue_job() calls RPUSH to add a job back to the queue.
from app.queue import dequeue_job, enqueue_job

# Reuse the existing database infrastructure – no second engine or config.
# SessionLocal is the SQLAlchemy session factory defined in database.py.
from app.database import SessionLocal

# The Job ORM model maps to the "jobs" table in PostgreSQL.
from app.models import Job

# Scientific computation workload
from app.compute import dispatch_job

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Maximum number of retry attempts before a job transitions permanently to failed.
MAX_RETRIES = 3

# How long (in seconds) to sleep when the queue is empty before polling again.
POLL_INTERVAL_SECONDS = 2


def claim_job(db: Session, job_id: int) -> bool:
    """
    Atomically transition a job from 'queued' to 'running' in PostgreSQL.

    Executes a single conditional UPDATE statement:
        UPDATE jobs
        SET status = 'running', started_at = :now
        WHERE id = :job_id AND status = 'queued'

    Returns:
        True if exactly 1 row was updated (job successfully claimed),
        False if 0 rows were updated (already claimed, completed, or not queued).
    """
    stmt = (
        update(Job)
        .where(Job.id == job_id, Job.status == "queued")
        .values(status="running", started_at=datetime.now(timezone.utc))
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount == 1


def process_job(job_id: int) -> None:
    """
    Atomically claim a Job in PostgreSQL and run scientific computation.

    Steps:
      1. Open a SQLAlchemy session.
      2. Atomically claim the job (status 'queued' -> 'running').
      3. If claim fails (0 rows updated), skip execution.
      4. Fetch the claimed job row.
      5. Execute scientific computation with job.input_data.
      6. Transition to 'completed' or handle retry / failure.
    """
    # Open a session manually (not via FastAPI's Depends) because the worker
    # runs outside the HTTP request/response cycle.
    db = SessionLocal()
    try:
        # ── 1. Atomically claim the job: queued → running ─────────────────────
        if not claim_job(db, job_id):
            logger.warning(
                "job_id=%d could not be claimed (not 'queued' or does not exist) – skipping.",
                job_id,
            )
            return

        # ── 2. Fetch the claimed Job row ──────────────────────────────────────
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job_id=%d not found in PostgreSQL – skipping.", job_id)
            return

        logger.info(
            "job_id=%d | queued → running | type=%r | started_at=%s",
            job.id,
            job.job_type,
            job.started_at.isoformat() if job.started_at else "",
        )

        # ── 4. Execute scientific computation & update status ─────────────────
        try:
            result = dispatch_job(job.job_type, job.input_data)
            logger.info("job_id=%d | computation completed | result=%s", job.id, result)

            # ── 5. Transition: running → completed ────────────────────────────
            job.result = result
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                "job_id=%d | running → completed | completed_at=%s",
                job.id,
                job.completed_at.isoformat(),
            )
        except Exception as exc:
            logger.exception("job_id=%d | computation failed: %s", job.id, exc)
            job.error_message = str(exc)
            job.result = None
            job.completed_at = None

            if job.retry_count < MAX_RETRIES:
                job.retry_count += 1
                job.status = "queued"
                job.started_at = None
                db.commit()

                enqueue_job(job.id)
                logger.info(
                    "job_id=%d | retry %d/%d | running → queued (re-enqueued) | error=%s",
                    job.id,
                    job.retry_count,
                    MAX_RETRIES,
                    job.error_message,
                )
            else:
                job.status = "failed"
                db.commit()
                logger.info(
                    "job_id=%d | max retries reached (%d/%d) | running → failed | error=%s",
                    job.id,
                    job.retry_count,
                    MAX_RETRIES,
                    job.error_message,
                )

    finally:
        # Always close the session to return the connection to the pool.
        db.close()


def run_worker() -> None:
    """
    Main worker loop.

    Polls the Redis queue in a tight loop.  When a job ID is available it
    calls process_job(); when the queue is empty it sleeps for
    POLL_INTERVAL_SECONDS before trying again.
    """
    logger.info("Worker started.  Polling queue every %ds …", POLL_INTERVAL_SECONDS)

    while True:
        # dequeue_job() uses LPOP – non-blocking, returns None if queue is empty.
        job_id = dequeue_job()

        if job_id is not None:
            logger.info("Dequeued job_id=%d", job_id)
            process_job(job_id)
        else:
            # Queue is empty – wait a bit before polling again.
            logger.debug("Queue empty, sleeping %ds …", POLL_INTERVAL_SECONDS)
            time.sleep(POLL_INTERVAL_SECONDS)


# ── Entry point ───────────────────────────────────────────────────────────────
# Allows running the worker directly:  python -m app.worker
if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user (KeyboardInterrupt).")
