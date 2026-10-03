"""
app/recovery.py
===============
ComputeGrid Reliability & Fault Tolerance — Day 9

Module responsible for detecting and identifying stale/stuck running jobs in
the distributed compute platform.
"""

import logging
from datetime import datetime, timedelta, timezone
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.queue import enqueue_job

logger = logging.getLogger(__name__)

# Duration in minutes after which an uncompleted running job is considered stale.
STALE_JOB_TIMEOUT_MINUTES = 10


def find_stale_jobs(db: Session) -> list[Job]:
    """
    Detect and return all running jobs that have exceeded the stale timeout threshold.

    What a stale job means:
    -----------------------
    A "stale job" is a compute task that has transitioned to the "running" state
    and has a recorded `started_at` timestamp, but has remained uncompleted (`completed_at IS NULL`)
    for longer than `STALE_JOB_TIMEOUT_MINUTES`. This typically happens when a worker process
    crashes unexpectedly, gets terminated (OOM, machine restart), encounters an unhandled fatal
    signal, or hangs indefinitely without updating PostgreSQL.

    Why stale-job detection is needed:
    ----------------------------------
    In a distributed queue architecture, if a worker dies mid-execution, the job is left
    stranded in the "running" state in the database forever and is no longer present in Redis.
    Detecting stale jobs is the essential first step to monitor, alert on, and ultimately
    recover or requeue abandoned computational workloads.

    Scope & Safety:
    ---------------
    This function is strictly read-only: it ONLY queries and returns matching Job objects.
    It does NOT alter job statuses, modify database records, retry, or requeue any tasks.

    Parameters:
    -----------
    db : Session
        The active SQLAlchemy database session.

    Returns:
    --------
    list[Job]
        A list of Job ORM instances matching all stale running criteria.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)

    stmt = select(Job).where(
        Job.status == "running",
        Job.started_at.is_not(None),
        Job.completed_at.is_(None),
        Job.started_at < cutoff_time,
    )

    stale_jobs = list(db.scalars(stmt).all())
    if stale_jobs:
        logger.info("Found %d stale running job(s) eligible for recovery", len(stale_jobs))
    return stale_jobs


def recover_stale_job(db: Session, job_id: int) -> bool:
    """
    Recover a single stale running job by resetting its status to 'queued' and re-enqueuing it.

    Parameters:
    -----------
    db : Session
        The active SQLAlchemy database session.
    job_id : int
        The ID of the job to recover.

    Returns:
    --------
    bool
        True if the job was stale and successfully recovered and enqueued; False otherwise.
    """
    job = db.get(Job, job_id)
    if job is None:
        logger.warning("recover_stale_job: job_id=%d not found", job_id)
        return False

    if job.status != "running":
        logger.warning(
            "recover_stale_job: job_id=%d has status=%r (expected 'running')",
            job_id,
            job.status,
        )
        return False

    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES)
    if job.started_at is None or job.completed_at is not None or job.started_at >= cutoff_time:
        logger.warning(
            "recover_stale_job: job_id=%d is not stale (started_at=%s, completed_at=%s)",
            job_id,
            job.started_at,
            job.completed_at,
        )
        return False

    try:
        # Reset job state in PostgreSQL
        job.status = "queued"
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.result = None

        # Re-enqueue in Redis
        enqueue_job(job.id)

        # Commit PostgreSQL transaction
        db.commit()

        logger.info(
            "job_id=%d | recovered stale job | type=%s | status reset to 'queued' and enqueued to Redis",
            job.id,
            job.job_type,
        )
        return True

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to recover stale job_id=%d: %s", job_id, exc)
        return False

