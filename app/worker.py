"""
app/worker.py
=============
ComputeGrid Worker – Day 7 (initial skeleton)

Responsibility
--------------
This module is the *worker* process.  Its only job right now is to:

  1. Continuously poll the Redis queue for job IDs.
  2. Look up the corresponding Job row in PostgreSQL.
  3. Log useful information about the job (id, type, status, input data).

What it does NOT do yet
-----------------------
  - No scientific computation.
  - No PostgreSQL status updates (job status is read-only for now).

How to run
----------
From the project root (with your virtual environment active):

    python -m app.worker

Press Ctrl+C to stop the worker.
"""

import time
import logging
from datetime import datetime, timezone

# Reuse the existing queue abstraction.
# dequeue_job() calls LPOP on "computegrid:jobs" and returns an int or None.
from app.queue import dequeue_job

# Reuse the existing database infrastructure – no second engine or config.
# SessionLocal is the SQLAlchemy session factory defined in database.py.
from app.database import SessionLocal

# The Job ORM model maps to the "jobs" table in PostgreSQL.
from app.models import Job

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# How long (in seconds) to sleep when the queue is empty before polling again.
POLL_INTERVAL_SECONDS = 2


def process_job(job_id: int) -> None:
    """
    Transition a Job from 'queued' to 'running' in PostgreSQL.

    Steps:
      1. Open a SQLAlchemy session.
      2. Fetch the Job row by primary key.
      3. Guard: if the job doesn't exist, log a warning and return.
      4. Guard: if the job is not 'queued', log a warning and return.
      5. Set status = 'running' and started_at = current UTC time.
      6. Commit the change to PostgreSQL.
      7. Log the successful transition.

    In future tasks this function will also:
      - Run scientific computation.
      - Save the result and mark it as 'completed' or 'failed'.
    """
    # Open a session manually (not via FastAPI's Depends) because the worker
    # runs outside the HTTP request/response cycle.
    db = SessionLocal()
    try:
        # ── 1. Fetch the Job row by primary key ───────────────────────────────
        job = db.get(Job, job_id)

        if job is None:
            # The ID came from Redis but no matching row exists in PostgreSQL.
            # This should not happen in normal operation.
            logger.warning("job_id=%d not found in PostgreSQL – skipping.", job_id)
            return

        # ── 2. Guard: only transition jobs that are still 'queued' ────────────
        if job.status != "queued":
            logger.warning(
                "job_id=%d has status=%r (expected 'queued') – skipping to "
                "avoid incorrect state transition.",
                job_id,
                job.status,
            )
            return

        # ── 3. Transition: queued → running ───────────────────────────────────
        job.status = "running"
        # datetime.now(timezone.utc) is timezone-aware, matching the
        # DateTime(timezone=True) definition in models.py.
        job.started_at = datetime.now(timezone.utc)

        # Write the change to PostgreSQL.
        db.commit()

        logger.info(
            "job_id=%d | queued → running | type=%r | started_at=%s",
            job.id,
            job.job_type,
            job.started_at.isoformat(),
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
