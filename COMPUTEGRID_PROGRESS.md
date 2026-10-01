ComputeGrid Progress

Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are queued, processed by workers, and their status/results are stored persistently.

Current Phase

Day 12 — Additional Computation Workloads and Dispatching

Completed

Day 1 — Project Foundation and Database Foundation

Project Setup

Created GitHub repository

Cloned repository locally

Created Python virtual environment

Installed FastAPI and Uvicorn

Created initial FastAPI application

Created /health endpoint

Verified local FastAPI server

Verified FastAPI Swagger documentation at /docs

PostgreSQL Setup

Installed PostgreSQL

Added PostgreSQL bin directory to Windows PATH

Verified psql CLI

Verified PostgreSQL server using pg_isready

Created computegrid database

Connected to computegrid using psql

Database Design

Designed initial jobs table

Created jobs table

Added primary key with auto-generated identity

Added job type

Added job status

Added JSONB input data

Added JSONB result

Added error message field

Added job timestamps

Database Testing

Successfully inserted first test job

Verified job appears in PostgreSQL

Verified default job status is queued

Day 2 — FastAPI → PostgreSQL Integration

Added SQLAlchemy 2.x and Psycopg 3 dependencies.

Added pydantic-settings configuration.

Created app/config.py.

Created local .env configuration and .env.example.

Confirmed .env is Git-ignored.

Created app/database.py.

Created SQLAlchemy engine using PostgreSQL + Psycopg.

Created SessionLocal.

Created get_db() FastAPI database session dependency.

Verified a real SELECT 1 query against the computegrid database.

Integrated get_db() with FastAPI.

Preserved GET /health.

Added GET /health/db.

Verified both endpoints return HTTP 200.

Verified FastAPI can obtain a live PostgreSQL session through dependency injection.

Commit

754b978 Complete Day 2 FastAPI PostgreSQL integration

Day 3 — Job Model and Pydantic Schemas

Inspected the existing jobs table schema in PostgreSQL without modifying the database structure.

Created app/models.py with the SQLAlchemy Job ORM model.

Mapped the Job model to the existing jobs table.

Used SQLAlchemy 2.0 type annotations.

Created app/schemas.py.

Created JobBase, JobCreate and JobResponse Pydantic schemas.

Configured JobResponse for ORM/object serialization using from_attributes.

Verified SQLAlchemy recognition of the Job model.

Tested a read-only SELECT query using the Job ORM model.

Tested Pydantic serialization using JobResponse.model_validate().

Day 4 — Job Creation API

Created app/routers/init.py.

Created app/routers/jobs.py.

Created the /jobs FastAPI router.

Registered the jobs router in app/main.py.

Implemented POST /jobs.

Integrated JobCreate request validation.

Integrated JobResponse response serialization.

Integrated get_db().

Created SQLAlchemy Job objects from validated API input.

Committed new jobs to PostgreSQL.

Refreshed the SQLAlchemy object after commit.

Verified POST /jobs through Swagger.

Verified HTTP 201 Created response.

Verified database-generated job IDs.

Verified the default job status is queued.

Verified created jobs exist in PostgreSQL.

Confirmed result, error_message, started_at and completed_at are initially null.

Commit

8529380 Implement job creation API

Day 5 — Job Status API

Implemented GET /jobs/{job_id}.

Added the endpoint to app/routers/jobs.py.

Used the existing get_db() database dependency.

Retrieved jobs using the SQLAlchemy Job model.

Used db.get(Job, job_id).

Returned JobResponse.

Returned HTTP 200 for existing jobs.

Returned HTTP 404 for non-existent jobs.

Verified through FastAPI Swagger.

Verified PostgreSQL job retrieval.

Verified:

GET /jobs/9999

returns:

{"detail":"Job not found"}

Confirmed no database schema changes were required.

Confirmed no new dependencies were introduced.

Day 6 — Redis Queue

Installed the Python Redis client.

Added Redis configuration.

Created app/redis_client.py.

Added Redis health checking.

Created app/queue.py.

Created Redis queue:

computegrid

Implemented FIFO queue behavior using:

RPUSH

LPOP

Job submission flow:

POST /jobs

↓

Create job in PostgreSQL

↓

Commit PostgreSQL transaction

↓

Refresh job

↓

Enqueue job ID into Redis

↓

Return JobResponse

Important Decision

Only the integer job ID is stored in Redis.

The complete job remains in PostgreSQL.

PostgreSQL remains the source of truth.

Redis runs through Docker using:

computegrid-redis-stack

Redis port:

6379

Day 7 — Worker Process

Created app/worker.py.

Worker runs independently from FastAPI.

Worker continuously checks Redis for jobs.

Worker receives a job ID from Redis.

Worker loads the job from PostgreSQL.

Worker verifies that the job exists.

Worker verifies that the current status is queued.

Worker transitions:

QUEUED → RUNNING

Worker records started_at.

Worker commits the state change.

Worker closes the database session using finally.

Worker sleeps briefly when the queue is empty.

Run worker using:

python -m app.worker

Day 7 Lifecycle

QUEUED → RUNNING

Day 8 — Scientific Computation, Completion and Failure Handling

Objective

Move actual scientific computation into the worker and implement the complete job lifecycle.

Day 8 — Scientific Computation

Created:

app/compute.py

Implemented:

run_matrix_stats(input_data)

The function:

Reads the requested matrix size.

Validates that the matrix size is positive.

Generates a random NumPy matrix.

Calculates matrix statistics.

Returns a JSON-serializable dictionary.

Current result fields:

shape
mean
std
min
max
sum

NumPy values are converted to standard Python values so the result can be stored in PostgreSQL JSONB.

Day 8 — Worker Integration

Updated app/worker.py.

Imported run_matrix_stats from app.compute.

After the job transitions to running, the worker executes the scientific computation.

Scientific computation therefore runs inside the worker instead of blocking the FastAPI request.

Day 8 — Successful Job Completion

After successful computation:

job.result is populated.

job.status is changed from running to completed.

job.completed_at is recorded.

The completed state is committed to PostgreSQL.

Successful lifecycle:

QUEUED → RUNNING → COMPUTATION → COMPLETED

Completed jobs contain:

result

started_at

completed_at

Day 8 — Failure Handling

Wrapped the scientific computation and completion block in try/except Exception.

If computation fails:

job.status = failed

job.error_message = str(exc)

job.result = None

job.completed_at = None

The failure state is committed to PostgreSQL.

logger.exception() is used to record the exception and stack trace.

Failure lifecycle:

QUEUED → RUNNING → FAILED

Day 8 — Failure Test

Created test job:

job_id = 14

job_type = matrix_stats

input_data = {"size": 0}

The computation correctly raised:

ValueError: Matrix size must be a positive integer.

Worker verified:

job_id=14 | queued → running

job_id=14 | computation failed: Matrix size must be a positive integer.

job_id=14 | running → failed | error=Matrix size must be a positive integer.

PostgreSQL Verification

Job ID:

14

Status:

failed

Error message:

Matrix size must be a positive integer.

Result:

NULL

Started at:

NOT NULL

Completed at:

NULL

API Verification

GET /jobs/14

Returned:

{
"id": 14,
"job_type": "matrix_stats",
"status": "failed",
"input_data": {
"size": 0
},
"result": null,
"error_message": "Matrix size must be a positive integer.",
"created_at": "2026-09-27T22:42:38.724440+05:30",
"started_at": "2026-09-27T22:42:38.743812+05:30",
"completed_at": null
}

Day 8 Review

Reviewed:

app/compute.py

app/worker.py

app/queue.py

app/models.py

app/schemas.py

app/routers/jobs.py

COMPUTEGRID_PROGRESS.md

Review findings:

No accidental unrelated changes.

Database session cleanup is correct.

Timezone-aware timestamps are used.

Successful results are persisted correctly.

Failure errors are persisted correctly.

Redis/API architecture remains unchanged.

No obvious bugs or syntax issues were found.

Day 9 — Stale Job Detection and Recovery

Overview

Implemented reliability and fault tolerance mechanisms to detect and recover orphaned or stuck jobs left in the "running" state due to worker crashes, unhandled termination, or unexpected hangs.

Reliability Module

Created app/recovery.py.

Constants:

STALE_JOB_TIMEOUT_MINUTES = 10

Stale Job Detection:

find_stale_jobs(db):
- Finds jobs in PostgreSQL with status == "running".
- Requires started_at to be NOT NULL.
- Requires completed_at to be NULL.
- Treats running jobs older than the 10-minute timeout threshold (started_at < now(UTC) - STALE_JOB_TIMEOUT_MINUTES) as stale.
- Strictly read-only detection; does not modify any database records or queue states.

Stale Job Recovery:

recover_stale_job(db, job_id):
- Retrieves the specified job from PostgreSQL using SQLAlchemy.
- Only operates on jobs currently with status == "running".
- Verifies that the job is actually stale according to the timeout threshold.
- Resets stale job attributes:
    running → queued
    started_at → NULL
    completed_at → NULL
    error_message → NULL
    result → NULL
- Re-enqueues the job ID into Redis using the existing enqueue_job() queue abstraction.
- Commits the PostgreSQL transaction.
- Rolls back database changes on Redis or database failure to prevent orphaned state.
- Logs all recovery activity.
- Returns True on successful recovery and False when recovery is not applicable or fails.

Testing & Validation

Stale Job Detection:
- Scanned existing database records and identified 7 stale jobs: IDs 7, 8, 9, 10, 11, 12, and 15.

Controlled Recovery Lifecycle Test:
- Job 7 was selected for controlled recovery verification.
- Verified state transition:
    RUNNING → QUEUED
    job ID 7 was added to Redis queue (computegrid:jobs).
- The worker process was allowed to dequeue and execute the recovered job.
- Job 7 executed scientific computation and completed successfully.
- Demonstrated complete recovery lifecycle:
    RUNNING → stale → QUEUED → Redis → RUNNING → COMPLETED

Idempotency and Guard Testing:
- A second recovery attempt on Job 7 returned False after the worker had already completed it.
- PostgreSQL remained COMPLETED.
- Redis contained zero copies of Job 7.
- The test script reported FAILED only because the script's assertion expected Job 7 to still be QUEUED (since the worker had already picked up and completed the job in the background); the recovery function itself correctly and safely refused to modify a non-running / completed job.

Temporary Test Scripts:
- test_recovery.py: manual script for read-only detection and single-job recovery verification.
- test_recovery_idempotency.py: verification script for guard logic on non-stale/completed jobs.
(Note: These are temporary standalone scripts and are not part of permanent production test suites).

Important Reliability Note

PostgreSQL and Redis are separate distributed systems, so the recovery transaction is not globally atomic across both systems. A future outbox/coordination mechanism may be considered if stronger distributed transaction guarantees are required.

Day 9 Review

- No database schema changes were required.
- Existing files (app/models.py, app/worker.py, app/queue.py) remained unchanged.
- PostgreSQL remains the authoritative source of truth.
- Redis continues to store only job IDs.

Day 10 — Job Retry and Requeue Mechanism

Overview

Implemented an automated bounded retry and requeue mechanism for failed computational jobs to handle transient execution errors and failures cleanly with persistent attempt tracking.

Database Schema & Model Changes

- Added `retry_count` column to the PostgreSQL `jobs` table:
  `jobs.retry_count INTEGER NOT NULL DEFAULT 0`
- Updated `Job` model in `app/models.py` with SQLAlchemy 2.x `Mapped[int]` column mapping and `server_default=text("0")`.
- Existing jobs safely defaulted to `retry_count = 0`.

Worker Retry Logic

- Updated `app/worker.py` with `MAX_RETRIES = 3`.
- Updated computation exception handler in `process_job()`:
  - If `job.retry_count < MAX_RETRIES`:
    - Increments `job.retry_count += 1`.
    - Resets `job.status` to `"queued"`.
    - Clears `job.started_at`, `job.completed_at`, and `job.result`.
    - Preserves `job.error_message` for diagnostic visibility and debugging.
    - Commits PostgreSQL transaction state.
    - Re-enqueues the job ID into Redis using `enqueue_job(job.id)`.
    - Logs retry attempt (`retry X/3`).
  - If `job.retry_count >= MAX_RETRIES`:
    - Sets `job.status` permanently to `"failed"`.
    - Retains `job.error_message`.
    - Commits PostgreSQL transaction state.
    - Does not re-enqueue into Redis.

Testing & Validation

- Created a temporary test script (`test_retry.py`) submitting a job configured to trigger a computation error (`matrix_stats` with input `{"size": 0}`).
- Verified with `job_id=19`:
  - Initial attempt + 3 retries = 4 total executions.
  - Initial execution (`retry_count=0`): Failed with `ValueError: Matrix size must be a positive integer.` → incremented to `retry_count=1`, status set to `queued`, re-enqueued.
  - Retry 1 (`retry_count=1`): Failed → incremented to `retry_count=2`, status set to `queued`, re-enqueued.
  - Retry 2 (`retry_count=2`): Failed → incremented to `retry_count=3`, status set to `queued`, re-enqueued.
  - Retry 3 (`retry_count=3`): Failed → reached `MAX_RETRIES` (3), status transitioned permanently to `failed`, not re-enqueued.
  - Verified final database state: `status = "failed"`, `retry_count = 3`, `error_message = "Matrix size must be a positive integer."`.
  - Verified Redis queue length returned to `0`.
- Temporary test files (`test_retry.py`, `test_recovery.py`, `test_recovery_idempotency.py`) were removed.
- No git commits or pushes have been made yet.

Day 11 — Multiple-Worker Concurrency and Reliability

Overview

Implemented multi-worker concurrency protection and atomic PostgreSQL job-claiming logic to ensure safe parallel execution across multiple worker instances and prevent race conditions or duplicate job processing.

Atomic PostgreSQL Job Claiming

- Added `claim_job(db: Session, job_id: int) -> bool` helper in `app/worker.py`.
- Implemented atomic transition (`queued` → `running`) using a single conditional SQL `UPDATE`:
  ```sql
  UPDATE jobs
  SET status = 'running', started_at = :now
  WHERE id = :job_id AND status = 'queued'
  ```
- Evaluated update result:
  - If `rowcount == 1`: The worker successfully claimed the job.
  - If `rowcount == 0`: The job was already claimed, completed, or otherwise not queued; the worker safely skips execution.
- Preserved `started_at` timestamp setting upon successful claim.
- Leveraged PostgreSQL row-level locking during `UPDATE` to prevent race conditions without introducing external distributed locks or additional dependencies.

Multiple-Worker Concurrency & Race-Condition Testing

- Multiple-Worker Concurrency Test:
  - Started multiple worker processes simultaneously polling `computegrid:jobs`.
  - Verified distributed job consumption across active workers.
- Race-Condition & Duplicate Protection Test (Job 26):
  - Injected duplicate / concurrent claim scenarios for `job_id=26` across multiple running workers.
  - Test result:
    - Worker 1 successfully matched `WHERE id = 26 AND status = 'queued'`, updated 1 row (`claim_job` returned `True`), claimed the job, executed `run_matrix_stats()`, and transitioned the job to `completed`.
    - Worker 2 attempted to claim the same job, matched 0 rows because the job was no longer `queued` (`claim_job` returned `False`), and safely skipped execution.
    - Verified that `job_id=26` was executed exactly once with zero duplicate processing and consistent database state.

Day 11 Review

- Reviewed:
  - `app/worker.py`
  - `COMPUTEGRID_PROGRESS.md`
- Review findings:
  - Atomic conditional update prevents multiple workers from simultaneously claiming the same queued job.
  - Database integrity is maintained under multi-worker concurrency.
  - Existing retry logic (`MAX_RETRIES = 3`) and stale job recovery remain fully compatible.
  - No new dependencies or architectural breaking changes were introduced.

Day 12 — Additional Computation Workloads and Dispatching

Completed:
- Added `matrix_multiply` scientific workload.
- Added `data_stats` scientific workload.
- Added dictionary-based `DISPATCH_TABLE`.
- Added `dispatch_job(job_type, input_data)`.
- Updated worker to dispatch workloads based on `job.job_type`.
- Preserved atomic job claiming and existing retry/failure logic.

Testing:
- `matrix_stats` → completed successfully.
- `matrix_multiply` → completed successfully.
- `data_stats` → completed successfully.
- Unsupported `unknown_workload` → correctly retried 3 times and then failed.
- Verified final failure had `retry_count = 3`, `result = null`, and the expected error message.

Architecture now supports:
`job_type → dispatch_job() → selected scientific workload`

Current Architecture

Client

↓

FastAPI

↓

PostgreSQL

(source of truth)

↓

Redis Queue
(computegrid:jobs)

↓

Worker

↓

Scientific Computation
(job_type → dispatch_job() → selected workload)

↓

PostgreSQL

(result/status)

Current Job Lifecycle

POST /jobs

↓

PostgreSQL

↓

QUEUED

↓

Redis

↓

Worker

↓

RUNNING

↓

Scientific Computation
(dispatch_job)

├──→ COMPLETED
│     ├── result
│     └── completed_at
│
└──→ EXCEPTION / FAILURE
      ├── retry_count < MAX_RETRIES (3) ──→ QUEUED (re-enqueued into Redis, retry_count += 1)
      └── retry_count >= MAX_RETRIES (3) ──→ FAILED (error_message preserved, not re-enqueued)

Stale Job Recovery Lifecycle:

RUNNING (stale / crashed worker)

↓

find_stale_jobs() / recover_stale_job()

↓

QUEUED (PostgreSQL reset)

↓

Redis (re-enqueued)

↓

Worker (re-processed)

↓

COMPLETED / FAILED

Current Database

Database:

computegrid

Table:

jobs

Important fields:

id

job_type

status

retry_count

input_data

result

error_message

created_at

started_at

completed_at

Current API

GET /health

GET /health/db

GET /health/redis

POST /jobs

GET /jobs/{job_id}

Current Task

Day 12 — Additional Computation Workloads and Dispatching completed.

Next Tasks

- Day 13: Automated test suite + GitHub Actions CI
- Day 14: Performance/observability + Dockerization/integration
- Later: final cleanup, documentation, and project review

Important Decisions

Python is the primary language.

FastAPI provides the API layer.

PostgreSQL stores persistent job information and remains the source of truth.

Redis handles job queueing.

Workers execute computational jobs.

NumPy is used for scientific workloads.

Workers are independent processes from FastAPI.

Redis stores job IDs rather than complete job data.

Database sessions in workers are explicitly closed.

Scientific computation is not performed inside the API request.

Known Future Improvements

More job types and computation dispatching.

Automated tests.

Improved logging and observability.

Dockerizing the complete application.

GitHub Actions CI/CD.

Performance and load testing.

Additional distributed-system reliability mechanisms (e.g. transactional outbox).

Known Issues

No blocking issues identified in the Day 10 implementation.

Setup

Create and activate the virtual environment:

python -m venv .venv

.venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

Run FastAPI:

uvicorn app.main --reload

Run worker in a separate terminal:

python -m app.worker

FastAPI documentation:

/docs

PostgreSQL

Connect to PostgreSQL:

psql -U postgres

Connect to ComputeGrid:

\c computegrid

Check jobs table:

\d jobs

View jobs:

SELECT * FROM jobs;

Redis

Check Docker container:

docker ps

Start Redis container if required:

docker start computegrid-redis-stack

Open Redis CLI:

docker exec -it computegrid-redis-stack redis-cli

Check Redis:

PING

Check queue:

LRANGE computegrid:jobs 0 -1

Check queue length:

LLEN computegrid:jobs

Exit:

exit