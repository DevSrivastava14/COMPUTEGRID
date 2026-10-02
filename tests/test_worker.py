"""
tests/test_worker.py
====================
Day 13 – Tests for app/worker.py finite/testable functions.

Covers:
  claim_job()
    - successfully claims a queued job (returns True)
    - claimed job transitions to "running"
    - started_at is set after claiming
    - already-running job cannot be claimed (returns False)
    - completed job cannot be claimed (returns False)
    - nonexistent job cannot be claimed (returns False)

  process_job()
    - successful dispatch marks job "completed"
    - result dict is persisted to the DB
    - completed_at is set
    - each workload type in DISPATCH_TABLE is dispatched correctly
    - unsupported job_type triggers the failure/retry path (status "queued", retry_count++, re-enqueues)
    - failed job increments retry_count on each failure
    - job becomes permanently "failed" after MAX_RETRIES exhausted
    - error_message is persisted on failure
    - permanently-failed job has retry_count == MAX_RETRIES
    - job that cannot be claimed is skipped (no state change)
"""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Job
from app.worker import MAX_RETRIES, claim_job, process_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_queued_job(db: Session, job_type: str = "matrix_stats", **kwargs) -> Job:
    """Commit a queued Job and return it. Caller must clean up."""
    job = Job(job_type=job_type, status="queued", **kwargs)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _cleanup(db: Session, job_id: int) -> None:
    """Delete a committed row using a fresh session to avoid invalid-session issues."""
    s = SessionLocal()
    try:
        j = s.get(Job, job_id)
        if j:
            s.delete(j)
            s.commit()
    finally:
        s.close()


def _fresh_get(job_id: int) -> Job | None:
    """Return a fresh view of a Job row using a separate session."""
    s = SessionLocal()
    try:
        j = s.get(Job, job_id)
        # Detach so we can read attributes after session close
        if j:
            s.expunge(j)
        return j
    finally:
        s.close()


# ---------------------------------------------------------------------------
# claim_job() tests  (use db_session directly – claim_job accepts a Session)
# ---------------------------------------------------------------------------


class TestClaimJob:
    def test_claim_queued_job_returns_true(self, db_session: Session):
        job = _make_queued_job(db_session)
        try:
            result = claim_job(db_session, job.id)
            assert result is True
        finally:
            _cleanup(db_session, job.id)

    def test_claim_sets_status_to_running(self, db_session: Session):
        job = _make_queued_job(db_session)
        try:
            claim_job(db_session, job.id)
            db_session.refresh(job)
            assert job.status == "running"
        finally:
            _cleanup(db_session, job.id)

    def test_claim_sets_started_at(self, db_session: Session):
        job = _make_queued_job(db_session)
        try:
            claim_job(db_session, job.id)
            db_session.refresh(job)
            assert job.started_at is not None
            assert isinstance(job.started_at, datetime)
        finally:
            _cleanup(db_session, job.id)

    def test_claim_already_running_job_returns_false(self, db_session: Session):
        """A job already in 'running' status cannot be claimed again."""
        s = SessionLocal()
        try:
            job = Job(job_type="matrix_stats", status="running",
                      started_at=datetime.now(timezone.utc))
            s.add(job)
            s.commit()
            s.refresh(job)
            jid = job.id
            result = claim_job(s, jid)
            assert result is False
        finally:
            j = s.get(Job, jid)
            if j:
                s.delete(j)
                s.commit()
            s.close()

    def test_claim_completed_job_returns_false(self, db_session: Session):
        s = SessionLocal()
        try:
            job = Job(job_type="matrix_stats", status="completed",
                      started_at=datetime.now(timezone.utc),
                      completed_at=datetime.now(timezone.utc))
            s.add(job)
            s.commit()
            s.refresh(job)
            jid = job.id
            result = claim_job(s, jid)
            assert result is False
        finally:
            j = s.get(Job, jid)
            if j:
                s.delete(j)
                s.commit()
            s.close()

    def test_claim_nonexistent_job_returns_false(self, db_session: Session):
        result = claim_job(db_session, 999_999_999)
        assert result is False


# ---------------------------------------------------------------------------
# process_job() – success path
# (process_job opens its own SessionLocal; patch enqueue_job to avoid Redis)
# ---------------------------------------------------------------------------


class TestProcessJobSuccess:
    def _run(self, job_type: str, input_data: dict | None = None) -> int:
        """Helper: create a queued job, run process_job, return job_id."""
        s = SessionLocal()
        try:
            job = Job(job_type=job_type, status="queued", input_data=input_data)
            s.add(job)
            s.commit()
            s.refresh(job)
            return job.id
        finally:
            s.close()

    def test_successful_job_is_completed(self):
        jid = self._run("matrix_stats", {"size": 5})
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.status == "completed"
        finally:
            _cleanup(None, jid)

    def test_successful_job_persists_result(self):
        jid = self._run("matrix_stats", {"size": 5})
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.result is not None
            assert isinstance(job.result, dict)
        finally:
            _cleanup(None, jid)

    def test_successful_job_sets_completed_at(self):
        jid = self._run("matrix_stats", {"size": 5})
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.completed_at is not None
        finally:
            _cleanup(None, jid)

    @pytest.mark.parametrize("job_type,expected_key", [
        ("matrix_stats",     "shape"),
        ("matrix_multiply",  "shape"),
        ("data_stats",       "size"),
    ])
    def test_dispatch_table_job_types(self, job_type: str, expected_key: str):
        """Each supported job_type is dispatched and produces expected result keys."""
        jid = self._run(job_type, {"size": 4})
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.status == "completed"
            assert expected_key in job.result
        finally:
            _cleanup(None, jid)


# ---------------------------------------------------------------------------
# process_job() – failure / retry path
# ---------------------------------------------------------------------------


class TestProcessJobFailureAndRetry:
    def _make_job(self, retry_count: int = 0) -> int:
        s = SessionLocal()
        try:
            job = Job(job_type="unsupported_type", status="queued", retry_count=retry_count)
            s.add(job)
            s.commit()
            s.refresh(job)
            return job.id
        finally:
            s.close()

    def test_first_failure_increments_retry_count(self):
        jid = self._make_job(retry_count=0)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.retry_count == 1
        finally:
            _cleanup(None, jid)

    def test_first_failure_resets_status_to_queued(self):
        jid = self._make_job(retry_count=0)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.status == "queued"
        finally:
            _cleanup(None, jid)

    def test_first_failure_persists_error_message(self):
        jid = self._make_job(retry_count=0)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.error_message is not None
            assert len(job.error_message) > 0
        finally:
            _cleanup(None, jid)

    def test_first_failure_reenqueues_job(self):
        jid = self._make_job(retry_count=0)
        try:
            with patch("app.worker.enqueue_job") as mock_enq:
                process_job(jid)
            mock_enq.assert_called_once_with(jid)
        finally:
            _cleanup(None, jid)

    def test_retry_clears_started_at(self):
        jid = self._make_job(retry_count=0)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.started_at is None
        finally:
            _cleanup(None, jid)

    def test_exhausted_retries_marks_failed(self):
        """After MAX_RETRIES retries, the next attempt must permanently fail the job."""
        jid = self._make_job(retry_count=MAX_RETRIES)
        try:
            with patch("app.worker.enqueue_job") as mock_enq:
                process_job(jid)
            job = _fresh_get(jid)
            assert job.status == "failed"
            mock_enq.assert_not_called()
        finally:
            _cleanup(None, jid)

    def test_exhausted_retries_preserves_retry_count(self):
        """retry_count must NOT be incremented further after permanent failure."""
        jid = self._make_job(retry_count=MAX_RETRIES)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.retry_count == MAX_RETRIES
        finally:
            _cleanup(None, jid)

    def test_exhausted_retries_persists_error_message(self):
        jid = self._make_job(retry_count=MAX_RETRIES)
        try:
            with patch("app.worker.enqueue_job"):
                process_job(jid)
            job = _fresh_get(jid)
            assert job.error_message is not None
        finally:
            _cleanup(None, jid)

    def test_sequential_retries_increment_count_each_time(self):
        """
        Simulate the full retry cycle manually:
        attempt 1: retry_count 0 → 1
        attempt 2: retry_count 1 → 2
        attempt 3: retry_count 2 → 3
        attempt 4: retry_count 3 → failed (no increment)
        """
        jid = self._make_job(retry_count=0)
        try:
            for expected_count in range(1, MAX_RETRIES + 1):
                with patch("app.worker.enqueue_job"):
                    process_job(jid)
                job = _fresh_get(jid)
                assert job.retry_count == expected_count
                assert job.status == "queued", f"Expected queued at retry {expected_count}"

            # Final attempt – should permanently fail
            with patch("app.worker.enqueue_job") as mock_enq:
                process_job(jid)
            job = _fresh_get(jid)
            assert job.status == "failed"
            assert job.retry_count == MAX_RETRIES
            mock_enq.assert_not_called()
        finally:
            _cleanup(None, jid)


# ---------------------------------------------------------------------------
# process_job() – unclaimed / skip behavior
# ---------------------------------------------------------------------------


class TestProcessJobSkipBehavior:
    def test_nonexistent_job_is_skipped(self):
        """process_job with an ID that doesn't exist must not raise."""
        with patch("app.worker.enqueue_job"):
            process_job(999_999_998)  # should log a warning and return cleanly

    def test_already_running_job_is_skipped(self):
        """If a job is already 'running' (claimed by another worker), skip it."""
        s = SessionLocal()
        try:
            job = Job(job_type="matrix_stats", status="running",
                      started_at=datetime.now(timezone.utc))
            s.add(job)
            s.commit()
            s.refresh(job)
            jid = job.id
        finally:
            s.close()

        try:
            with patch("app.worker.enqueue_job") as mock_enq:
                process_job(jid)
            job = _fresh_get(jid)
            # Status must remain "running" – claim was refused
            assert job.status == "running"
            mock_enq.assert_not_called()
        finally:
            _cleanup(None, jid)
