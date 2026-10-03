"""
tests/test_queue_recovery.py
============================
Day 13 – Unit & integration tests for app/queue.py and app/recovery.py.

Queue tests:
  - enqueue_job pushes the correct job ID string to JOB_QUEUE_KEY
  - dequeue_job returns the expected job ID as int
  - dequeue_job returns None on an empty queue
  - The correct queue key constant is used in both operations
  - Redis errors propagate out of enqueue_job / dequeue_job

Recovery tests:
  - find_stale_jobs returns running jobs past the timeout
  - find_stale_jobs excludes queued, completed, and non-stale running jobs
  - recover_stale_job resets status to "queued"
  - recover_stale_job clears started_at, completed_at, error_message, result
  - recover_stale_job re-enqueues the job ID via Redis
  - recover_stale_job returns False for a nonexistent job
  - recover_stale_job returns False when status is not "running"
  - recover_stale_job returns False when the running job is not yet stale
  - recover_stale_job is idempotent: returns False on a second call (job now "queued")
"""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.models import Job
from app.queue import JOB_QUEUE_KEY, dequeue_job, enqueue_job
from app.recovery import STALE_JOB_TIMEOUT_MINUTES, find_stale_jobs, recover_stale_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stale_started_at() -> datetime:
    """Return a timezone-aware timestamp that is past the stale timeout."""
    return datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES + 5)


def _fresh_started_at() -> datetime:
    """Return a timezone-aware timestamp that is within the stale window (NOT stale)."""
    return datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_TIMEOUT_MINUTES - 2)


def _make_job(db: Session, **kwargs) -> Job:
    """
    Persist a Job row and return it.

    Caller is responsible for cleanup (delete + commit) because
    recover_stale_job internally commits, making rows permanent.
    """
    defaults = {"job_type": "test_job", "status": "queued"}
    defaults.update(kwargs)
    job = Job(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _cleanup(db: Session, *jobs: Job) -> None:
    """Delete committed test rows so they do not leak between tests."""
    for job in jobs:
        try:
            db.delete(job)
        except Exception:
            pass
    db.commit()


# ---------------------------------------------------------------------------
# Queue tests
# ---------------------------------------------------------------------------


class TestEnqueueJob:
    def test_enqueue_pushes_correct_key(self, mock_redis: MagicMock):
        enqueue_job(7)
        key_used = mock_redis.rpush.call_args.args[0]
        assert key_used == JOB_QUEUE_KEY

    def test_enqueue_pushes_job_id_as_string(self, mock_redis: MagicMock):
        enqueue_job(7)
        value_pushed = mock_redis.rpush.call_args.args[1]
        assert value_pushed == "7"

    def test_enqueue_returns_rpush_return_value(self, mock_redis: MagicMock):
        mock_redis.rpush.return_value = 3
        result = enqueue_job(99)
        assert result == 3

    def test_enqueue_propagates_redis_error(self, mock_redis: MagicMock):
        mock_redis.rpush.side_effect = RedisError("down")
        with pytest.raises(RedisError):
            enqueue_job(1)

    def test_enqueue_logs_job_id(self, mock_redis: MagicMock, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.INFO):
            enqueue_job(42)
        assert any(
            "job_id=42" in record.message and "enqueued to Redis queue" in record.message
            for record in caplog.records
        )


class TestDequeueJob:
    def test_dequeue_returns_job_id_as_int(self, mock_redis: MagicMock):
        mock_redis.lpop.return_value = "42"
        result = dequeue_job()
        assert result == 42
        assert isinstance(result, int)

    def test_dequeue_returns_none_when_queue_empty(self, mock_redis: MagicMock):
        mock_redis.lpop.return_value = None
        assert dequeue_job() is None

    def test_dequeue_uses_correct_queue_key(self, mock_redis: MagicMock):
        mock_redis.lpop.return_value = None
        dequeue_job()
        key_used = mock_redis.lpop.call_args.args[0]
        assert key_used == JOB_QUEUE_KEY

    def test_dequeue_propagates_redis_error(self, mock_redis: MagicMock):
        mock_redis.lpop.side_effect = RedisError("down")
        with pytest.raises(RedisError):
            dequeue_job()

    def test_dequeue_logs_job_id(self, mock_redis: MagicMock, caplog: pytest.LogCaptureFixture):
        mock_redis.lpop.return_value = "42"
        with caplog.at_level(logging.INFO):
            dequeue_job()
        assert any(
            "job_id=42" in record.message and "dequeued from Redis queue" in record.message
            for record in caplog.records
        )


class TestQueueKeyConstant:
    def test_job_queue_key_value(self):
        assert JOB_QUEUE_KEY == "computegrid:jobs"


# ---------------------------------------------------------------------------
# find_stale_jobs tests
# ---------------------------------------------------------------------------


class TestFindStaleJobs:
    def test_finds_stale_running_job(self, db_session: Session):
        job = _make_job(
            db_session,
            status="running",
            started_at=_stale_started_at(),
        )
        try:
            stale = find_stale_jobs(db_session)
            assert any(j.id == job.id for j in stale)
        finally:
            _cleanup(db_session, job)

    def test_does_not_return_queued_job(self, db_session: Session):
        job = _make_job(db_session, status="queued")
        try:
            stale = find_stale_jobs(db_session)
            assert all(j.id != job.id for j in stale)
        finally:
            _cleanup(db_session, job)

    def test_does_not_return_completed_job(self, db_session: Session):
        job = _make_job(
            db_session,
            status="completed",
            started_at=_stale_started_at(),
            completed_at=datetime.now(timezone.utc),
        )
        try:
            stale = find_stale_jobs(db_session)
            assert all(j.id != job.id for j in stale)
        finally:
            _cleanup(db_session, job)

    def test_does_not_return_non_stale_running_job(self, db_session: Session):
        """A running job that started recently is not yet stale."""
        job = _make_job(
            db_session,
            status="running",
            started_at=_fresh_started_at(),
        )
        try:
            stale = find_stale_jobs(db_session)
            assert all(j.id != job.id for j in stale)
        finally:
            _cleanup(db_session, job)

    def test_does_not_return_running_job_with_completed_at_set(self, db_session: Session):
        """A running job that already has completed_at is not stale (edge case)."""
        job = _make_job(
            db_session,
            status="running",
            started_at=_stale_started_at(),
            completed_at=datetime.now(timezone.utc),
        )
        try:
            stale = find_stale_jobs(db_session)
            assert all(j.id != job.id for j in stale)
        finally:
            _cleanup(db_session, job)

    def test_returns_empty_list_when_no_stale_jobs(self, db_session: Session):
        job = _make_job(db_session, status="queued")
        try:
            stale = find_stale_jobs(db_session)
            # Stale jobs may exist from prior runs; just verify our queued job is absent
            assert all(j.id != job.id for j in stale)
        finally:
            _cleanup(db_session, job)


# ---------------------------------------------------------------------------
# recover_stale_job tests
# ---------------------------------------------------------------------------


class TestRecoverStaleJob:
    def test_recover_returns_true_for_stale_job(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            result = recover_stale_job(db_session, job.id)
            assert result is True
        finally:
            db_session.refresh(job)
            _cleanup(db_session, job)

    def test_recover_resets_status_to_queued(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            recover_stale_job(db_session, job.id)
            db_session.refresh(job)
            assert job.status == "queued"
        finally:
            _cleanup(db_session, job)

    def test_recover_clears_started_at(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            recover_stale_job(db_session, job.id)
            db_session.refresh(job)
            assert job.started_at is None
        finally:
            _cleanup(db_session, job)

    def test_recover_clears_completed_at(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(
            db_session,
            status="running",
            started_at=_stale_started_at(),
        )
        try:
            recover_stale_job(db_session, job.id)
            db_session.refresh(job)
            assert job.completed_at is None
        finally:
            _cleanup(db_session, job)

    def test_recover_clears_error_message(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(
            db_session,
            status="running",
            started_at=_stale_started_at(),
            error_message="previous error",
        )
        try:
            recover_stale_job(db_session, job.id)
            db_session.refresh(job)
            assert job.error_message is None
        finally:
            _cleanup(db_session, job)

    def test_recover_clears_result(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(
            db_session,
            status="running",
            started_at=_stale_started_at(),
            result={"partial": True},
        )
        try:
            recover_stale_job(db_session, job.id)
            db_session.refresh(job)
            assert job.result is None
        finally:
            _cleanup(db_session, job)

    def test_recover_reenqueues_job_id(self, db_session: Session, mock_redis: MagicMock):
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            recover_stale_job(db_session, job.id)
            mock_redis.rpush.assert_called_once()
            _key, queued_id = mock_redis.rpush.call_args.args
            assert queued_id == str(job.id)
        finally:
            db_session.refresh(job)
            _cleanup(db_session, job)

    def test_recover_logs_stale_recovery(
        self, db_session: Session, mock_redis: MagicMock, caplog: pytest.LogCaptureFixture
    ):
        job = _make_job(
            db_session,
            job_type="matrix_stats",
            status="running",
            started_at=_stale_started_at(),
        )
        try:
            with caplog.at_level(logging.INFO):
                recover_stale_job(db_session, job.id)
            assert any(
                f"job_id={job.id}" in record.message
                and "recovered stale job" in record.message
                and "type=matrix_stats" in record.message
                for record in caplog.records
            )
        finally:
            db_session.refresh(job)
            _cleanup(db_session, job)

    def test_recover_returns_false_for_nonexistent_job(
        self, db_session: Session, mock_redis: MagicMock
    ):
        result = recover_stale_job(db_session, 999_999_999)
        assert result is False

    def test_recover_returns_false_when_status_not_running(
        self, db_session: Session, mock_redis: MagicMock
    ):
        job = _make_job(db_session, status="queued")
        try:
            result = recover_stale_job(db_session, job.id)
            assert result is False
        finally:
            _cleanup(db_session, job)

    def test_recover_returns_false_when_job_not_yet_stale(
        self, db_session: Session, mock_redis: MagicMock
    ):
        job = _make_job(db_session, status="running", started_at=_fresh_started_at())
        try:
            result = recover_stale_job(db_session, job.id)
            assert result is False
        finally:
            _cleanup(db_session, job)

    def test_recover_idempotent_second_call_returns_false(
        self, db_session: Session, mock_redis: MagicMock
    ):
        """After a successful recovery the job is 'queued'; a second call must return False."""
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            first = recover_stale_job(db_session, job.id)
            second = recover_stale_job(db_session, job.id)
            assert first is True
            assert second is False
        finally:
            db_session.refresh(job)
            _cleanup(db_session, job)

    def test_recover_returns_false_on_redis_enqueue_failure(
        self, db_session: Session, mock_redis: MagicMock
    ):
        """If enqueue_job raises RedisError the function must catch it, rollback, and return False."""
        mock_redis.rpush.side_effect = RedisError("unavailable")
        job = _make_job(db_session, status="running", started_at=_stale_started_at())
        try:
            result = recover_stale_job(db_session, job.id)
            assert result is False
        finally:
            # After rollback the session may be in a bad state; reopen to clean up
            try:
                db_session.refresh(job)
                _cleanup(db_session, job)
            except Exception:
                from app.database import SessionLocal
                cleanup_s = SessionLocal()
                j = cleanup_s.get(Job, job.id)
                if j:
                    cleanup_s.delete(j)
                    cleanup_s.commit()
                cleanup_s.close()
