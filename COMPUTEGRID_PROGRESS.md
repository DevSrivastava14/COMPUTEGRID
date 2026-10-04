ComputeGrid Progress

Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are queued, processed by workers, and their status/results are stored persistently.

Current Phase

Day 14 — Performance, Observability & Dockerization/Integration

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

Job submission flow

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

Current result fields

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

Constant:

STALE_JOB_TIMEOUT_MINUTES = 10

Stale Job Detection

find_stale_jobs(db):

Finds jobs in PostgreSQL with status == "running".

Requires started_at to be NOT NULL.

Requires completed_at to be NULL.

Treats running jobs older than the 10-minute timeout threshold (started_at < now(UTC) - STALE_JOB_TIMEOUT_MINUTES) as stale.

Strictly read-only detection; does not modify any database records or queue states.

Stale Job Recovery

recover_stale_job(db, job_id):

Retrieves the specified job from PostgreSQL using SQLAlchemy.

Only operates on jobs currently with status == "running".

Verifies that the job is actually stale according to the timeout threshold.

Resets stale job attributes:
running → queued
started_at → NULL
completed_at → NULL
error_message → NULL
result → NULL

Re-enqueues the job ID into Redis using the existing enqueue_job() queue abstraction.

Commits the PostgreSQL transaction.

Rolls back database changes on Redis or database failure to prevent orphaned state.

Logs all recovery activity.

Returns True on successful recovery and False when recovery is not applicable or fails.

Testing & Validation

Stale Job Detection:

Scanned existing database records and identified 7 stale jobs: IDs 7, 8, 9, 10, 11, 12, and 15.

Controlled Recovery Lifecycle Test:

Job 7 was selected for controlled recovery verification.

Verified state transition:
RUNNING → QUEUED
job ID 7 was added to Redis queue (computegrid).

The worker process was allowed to dequeue and execute the recovered job.

Job 7 executed scientific computation and completed successfully.

Demonstrated complete recovery lifecycle:
RUNNING → stale → QUEUED → Redis → RUNNING → COMPLETED

Idempotency and Guard Testing

A second recovery attempt on Job 7 returned False after the worker had already completed it.

PostgreSQL remained COMPLETED.

Redis contained zero copies of Job 7.

The test script reported FAILED only because the script's assertion expected Job 7 to still be QUEUED (since the worker had already picked up and completed the job in the background); the recovery function itself correctly and safely refused to modify a non-running / completed job.

Temporary Test Scripts

test_recovery.py: manual script for read-only detection and single-job recovery verification.

test_recovery_idempotency.py: verification script for guard logic on non-stale/completed jobs.

These were temporary standalone scripts and are not part of the permanent production test suite.

Important Reliability Note

PostgreSQL and Redis are separate distributed systems, so the recovery transaction is not globally atomic across both systems. A future outbox/coordination mechanism may be considered if stronger distributed transaction guarantees are required.

Day 9 Review

No database schema changes were required.

Existing files (app/models.py, app/worker.py, app/queue.py) remained unchanged.

PostgreSQL remains the authoritative source of truth.

Redis continues to store only job IDs.

Day 10 — Job Retry and Requeue Mechanism

Overview

Implemented an automated bounded retry and requeue mechanism for failed computational jobs to handle transient execution errors and failures cleanly with persistent attempt tracking.

Database Schema & Model Changes

Added retry_count column to the PostgreSQL jobs table:
jobs.retry_count INTEGER NOT NULL DEFAULT 0

Updated Job model in app/models.py with SQLAlchemy 2.x Mapped[int] column mapping and server_default=text("0").

Existing jobs safely defaulted to retry_count = 0.

Worker Retry Logic

Updated app/worker.py with MAX_RETRIES = 3.

Updated computation exception handler in process_job():

If job.retry_count < MAX_RETRIES:

Increments job.retry_count += 1.

Resets job.status to "queued".

Clears job.started_at, job.completed_at, and job.result.

Preserves job.error_message for diagnostic visibility and debugging.

Commits PostgreSQL transaction state.

Re-enqueues the job ID into Redis using enqueue_job(job.id).

Logs retry attempt (retry X/3).

If job.retry_count >= MAX_RETRIES:

Sets job.status permanently to "failed".

Retains job.error_message.

Commits PostgreSQL transaction state.

Does not re-enqueue the job ID into Redis.

Testing & Validation

Created a temporary test script (test_retry.py) submitting a job configured to trigger a computation error (matrix_stats with input {"size": 0}).

Verified with job_id=19:

Initial attempt + 3 retries = 4 total executions.

Initial execution (retry_count=0): Failed with ValueError: Matrix size must be a positive integer. → incremented to retry_count=1, status set to queued, re-enqueued.

Retry 1 (retry_count=1): Failed → incremented to retry_count=2, status set to queued, re-enqueued.

Retry 2 (retry_count=2): Failed → incremented to retry_count=3, status set to queued, re-enqueued.

Retry 3 (retry_count=3): Failed → reached MAX_RETRIES (3), status transitioned permanently to failed, not re-enqueued.

Verified final database state: status = "failed", retry_count = 3, error_message = "Matrix size must be a positive integer.".

Verified Redis queue length returned to 0.

Temporary test files (test_retry.py, test_recovery.py, test_recovery_idempotency.py) were removed.

No git commits or pushes were made yet.

Day 11 — Multiple-Worker Concurrency and Reliability

Overview

Implemented multi-worker concurrency protection and atomic PostgreSQL job-claiming logic to ensure safe parallel execution across multiple worker instances and prevent race conditions or duplicate job processing.

Atomic PostgreSQL Job Claiming

Added claim_job(db: Session, job_id: int) -> bool helper in app/worker.py.

Implemented atomic transition (queued → running) using a single conditional SQL UPDATE:

UPDATE jobs
SET status = 'running', started_at = :now
WHERE id = :job_id AND status = 'queued'

Evaluated update result:

If rowcount == 1: The worker successfully claimed the job.

If rowcount == 0: The job was already claimed, completed, or otherwise not queued; the worker safely skips execution.

Preserved started_at timestamp setting upon successful claim.

Leveraged PostgreSQL row-level locking during UPDATE to prevent race conditions without introducing external distributed locks or additional dependencies.

Multiple-Worker Concurrency & Race-Condition Testing

Multiple-Worker Concurrency Test:

Started multiple worker processes simultaneously polling computegrid:jobs.

Verified distributed job consumption across active workers.

Race-Condition & Duplicate Protection Test (Job 26):

Injected duplicate / concurrent claim scenarios for job_id=26 across multiple running workers.

Test result:

Worker 1 successfully matched WHERE id = 26 AND status = 'queued', updated 1 row (claim_job returned True), claimed the job, executed run_matrix_stats(), and transitioned the job to completed.

Worker 2 attempted to claim the same job, matched 0 rows because the job was no longer queued (claim_job returned False), and safely skipped execution.

Verified that job_id=26 was executed exactly once with zero duplicate processing and consistent database state.

Day 11 Review

Reviewed:

app/worker.py

COMPUTEGRID_PROGRESS.md

Review findings:

Atomic conditional update prevents multiple workers from simultaneously claiming the same queued job.

Database integrity is maintained under multi-worker concurrency.

Existing retry logic (MAX_RETRIES = 3) and stale job recovery remain fully compatible.

No new dependencies or architectural breaking changes were introduced.

Day 12 — Additional Computation Workloads and Dispatching

Completed

Added matrix_multiply scientific workload.

Added data_stats scientific workload.

Added dictionary-based DISPATCH_TABLE.

Added dispatch_job(job_type, input_data).

Updated worker to dispatch workloads based on job.job_type.

Preserved atomic job claiming and existing retry/failure logic.

Testing

matrix_stats → completed successfully.

matrix_multiply → completed successfully.

data_stats → completed successfully.

Unsupported unknown_workload → correctly retried 3 times and then failed.

Verified final failure had retry_count = 3, result = null, and the expected error message.

Architecture now supports:

job_type → dispatch_job() → selected scientific workload

Day 13 — Automated Test Suite + CI

Completed

Added pytest-based automated tests:

tests/test_compute.py — 38 tests

tests/test_api.py — 21 tests

tests/test_queue_recovery.py — 27 tests

tests/test_worker.py — 23 tests

Total:

109 tests

Verified result:

109 passed, 2 warnings

Added pytest, httpx, and numpy dependencies to requirements.txt as needed.

Added GitHub Actions workflow:

.github/workflows/ci.yml

CI includes:

Python 3.13 runner

PostgreSQL 16 service container

Dependency installation

Database schema creation

Pytest execution

Tests mock Redis where appropriate; the suite does not require a live Redis service.

Two dependency deprecation warnings (Starlette TestClient / AnyIO) were documented as non-blocking.

Git & Status

Commit:

790f58e — "Add automated test suite and CI"

Commit was pushed successfully to origin/main.

Working tree was clean.

Day 14 — Performance, Observability & Dockerization/Integration

Overview

Day 14 focused on establishing a basic performance baseline, improving structured job lifecycle observability, Dockerizing the application and worker, and creating a reproducible local multi-container environment.

The existing PostgreSQL source-of-truth architecture, Redis queue, worker processing, retry logic, stale recovery, and atomic job claiming were preserved.

Day 14 — Performance Baseline

API Job Submission Latency

Added lightweight performance instrumentation to:

app/routers/jobs.py

The create_job endpoint now measures overall job submission latency using Python's standard:

time.perf_counter()

The measured period covers the existing submission flow through PostgreSQL record creation, transaction commit, and Redis enqueueing.

Submission timing logs include:

job_id

job_type

duration in milliseconds

Redis enqueue failure timing is also logged when a Redis error occurs.

Worker Computation Duration

Added performance instrumentation to:

app/worker.py

The scientific computation dispatch inside process_job() is measured using:

time.perf_counter()

Timing is logged for both successful and failed computation paths.

Worker computation timing logs include:

job_id

job_type

duration in milliseconds

Performance Baseline Tests

Added tests verifying that timing information is logged for:

successful API job submission

successful worker computation

failed worker computation

Day 14 — Structured Job Lifecycle Logging

Improved standard Python logging across the job lifecycle.

Queue Logging

Updated:

app/queue.py

Added logs for:

enqueue_job()

and:

dequeue_job()

Queue logs include:

job_id

Redis queue name

enqueue/dequeue operation

API Logging

Updated:

app/routers/jobs.py

Preserved the performance timing logs and standardized useful job submission information.

Worker Logging

Updated:

app/worker.py

Improved logging for:

job dequeue

atomic job claim

transition from queued → running

computation completion

computation failure

retry

requeue

retry exhaustion

timestamps

job type

Redundant worker dequeue logging was removed so queue dequeue logging remains the single source for that event.

Recovery Logging

Updated:

app/recovery.py

Improved stale-job logging to include:

job_id

job_type

stale-job detection count

stale-job recovery activity

Logging Tests

Added tests covering important lifecycle logging behavior:

queue enqueue logging

queue dequeue logging

stale recovery logging

worker claim/running logging

worker retry/requeue logging

computation success timing logging

computation failure timing logging

API submission timing logging

Day 14 — Dockerization

Dockerfile

Created:

Dockerfile

The Docker image uses:

python:3.13-slim

Configured:

PYTHONDONTWRITEBYTECODE=1

PYTHONUNBUFFERED=1

/app working directory

dependency installation from requirements.txt

application source copied into the image

port 8000 exposed

The same image supports both:

FastAPI:

uvicorn app.main:app --host 0.0.0.0 --port 8000

and the worker:

python -m app.worker

Docker Ignore Rules

Created:

.dockerignore

Excluded:

.git

.github

.venv

Python cache files

.env

pytest cache

tests

Markdown documentation

Day 14 — Docker Compose Integration

Created:

docker-compose.yml

The Compose environment contains four services:

PostgreSQL

Redis

FastAPI API

Worker

PostgreSQL

Uses:

postgres:16-alpine

Configured database:

computegrid

Configured PostgreSQL user:

postgres

Configured PostgreSQL password for the local Compose environment:

postgres

Uses a named volume:

postgres_data

Added PostgreSQL healthcheck using:

pg_isready

Redis

Uses:

redis:7-alpine

Added Redis healthcheck using:

redis-cli ping

Redis remains internal to the Docker Compose network.

FastAPI

Builds from the ComputeGrid Dockerfile.

Exposes:

8000:8000

Uses Docker service names for internal connections:

DB_HOST=postgres

REDIS_HOST=redis

Depends on healthy PostgreSQL and Redis services.

Worker

Builds from the same Dockerfile.

Runs:

python -m app.worker

Uses:

DB_HOST=postgres

REDIS_HOST=redis

Depends on healthy PostgreSQL and Redis services.

Docker Networking

Docker service names are used instead of localhost for inter-container communication.

Therefore:

API/worker → postgres:5432

API/worker → redis:6379

The host only exposes the FastAPI port:

8000

This avoids host port collisions with existing local PostgreSQL and Redis services.

Day 14 — Database Initialization for Docker

Updated:

app/main.py

Added a FastAPI lifespan handler that initializes the existing SQLAlchemy metadata when the API container starts:

Base.metadata.create_all(bind=engine)

This allows the fresh PostgreSQL container used by the local Docker Compose environment to initialize the existing application tables automatically.

The change is intended for the reproducible local Docker development environment.

A future production deployment should use a dedicated database migration system rather than relying on application startup schema creation.

Day 14 — Docker Health Verification

Verified Docker Compose status:

computegrid-api-1 → running

computegrid-postgres-1 → healthy

computegrid-redis-1 → healthy

computegrid-worker-1 → running

Verified:

GET /health

returned:

200 OK

with:

{"status":"healthy"}

Verified:

GET /health/db

returned:

200 OK

with:

{"status":"healthy","database":"connected"}

Verified:

GET /health/redis

returned:

200 OK

with:

{"status":"healthy","redis":"connected"}

Day 14 — End-to-End Docker Job Processing

Submitted a real job through the Dockerized API.

Workload:

matrix_stats

Job ID:

1

Verified complete processing lifecycle:

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

Scientific computation

↓

COMPLETED

Worker log recorded computation completion in:

13.13ms

The completed job result was successfully persisted to PostgreSQL and returned through:

GET /jobs/1

Day 14 — Automated Test Suite

After all Day 14 application changes:

Total tests:

117

Verification result:

117 passed, 2 warnings

The two warnings are existing upstream dependency deprecation warnings related to:

Starlette TestClient / httpx

AnyIO BlockingPortal

They are non-blocking and do not currently affect the test results.

The Day 14 changes did not modify:

database schema structure

API contracts

Redis queue behavior

retry behavior

stale recovery behavior

atomic worker claiming

concurrency protection

Day 14 — Final Validation

Docker Compose stack successfully started.

PostgreSQL successfully reported healthy.

Redis successfully reported healthy.

FastAPI successfully started.

Worker successfully started.

All health endpoints returned successfully.

A real job completed successfully through the Dockerized API → Redis → worker → PostgreSQL flow.

Full test suite:

117 passed, 2 warnings

Working tree contains the expected Day 14 implementation changes.

Current Architecture

Client

↓

FastAPI

↓

PostgreSQL

(source of truth)

↓

Redis Queue

computegrid:jobs

↓

Worker

↓

Scientific Computation

job_type → dispatch_job() → selected workload

↓

PostgreSQL

(result/status)

Current Docker Architecture

                    ┌─────────────────┐
                    │     Client      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   FastAPI API   │
                    │   Port 8000     │
                    └───────┬─┬───────┘
                            │ │
                 ┌──────────┘ └──────────┐
                 ▼                       ▼
        ┌─────────────────┐     ┌─────────────────┐
        │   PostgreSQL    │     │      Redis      │
        │   Source of     │     │   Job Queue     │
        │     Truth       │     │ computegrid:jobs│
        └────────┬────────┘     └────────┬────────┘
                 ▲                       │
                 │                       ▼
                 │              ┌─────────────────┐
                 └──────────────│     Worker      │
                                │ Scientific Jobs │
                                └─────────────────┘

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

dispatch_job()

├──→ COMPLETED
│     ├── result
│     └── completed_at
│
└──→ EXCEPTION / FAILURE
├── retry_count < MAX_RETRIES (3)
│       └──→ QUEUED
│             └── re-enqueued into Redis
│                 retry_count += 1
│
└── retry_count >= MAX_RETRIES (3)
└──→ FAILED
├── error_message preserved
└── not re-enqueued

Stale Job Recovery Lifecycle

RUNNING

(stale / crashed worker)

↓

find_stale_jobs() / recover_stale_job()

↓

QUEUED

(PostgreSQL reset)

↓

Redis

(re-enqueued)

↓

Worker

(re-processed)

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

FastAPI documentation:

/docs

Current Scientific Workloads

Matrix Statistics

matrix_stats

Generates a numerical matrix and calculates:

shape

mean

standard deviation

minimum

maximum

sum

Matrix Multiplication

matrix_multiply

Performs parameterized matrix multiplication through the worker computation system.

Data Statistics

data_stats

Performs statistical analysis on generated numerical data.

Dispatch Architecture

job_type
   ↓
dispatch_job()
   ↓
DISPATCH_TABLE
   ↓
selected scientific workload

Current Reliability Features

ComputeGrid currently includes:

PostgreSQL source of truth

Redis job queue

Independent worker processes

Atomic PostgreSQL job claiming

Multiple-worker concurrency protection

Bounded retry mechanism

Retry count persistence

Stale job detection

Stale job recovery

Redis requeueing

Database transaction rollback on recovery failures

Structured lifecycle logging

Performance timing instrumentation

Health endpoints

Automated test suite

GitHub Actions CI

Dockerized API

Dockerized worker

Dockerized PostgreSQL

Dockerized Redis

Docker Compose integration

Setup

Option 1 — Local Development

Create and activate the virtual environment:

python -m venv .venv

.venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

Run FastAPI:

uvicorn app.main:app --reload

Run worker in a separate terminal:

python -m app.worker

FastAPI documentation:

http://localhost:8000/docs

Docker Compose Setup

The recommended reproducible local environment uses Docker Compose.

Start the complete ComputeGrid stack:

docker compose up --build

This starts:

PostgreSQL

Redis

FastAPI

Worker

Check running services:

docker compose ps

Expected services:

api
worker
postgres
redis

Stop the stack:

docker compose down

Stop the stack while preserving the PostgreSQL named volume:

docker compose down

The PostgreSQL data is stored in the Docker volume:

postgres_data

Docker Health Checks

Check API health:

http://localhost:8000/health

Check PostgreSQL connectivity:

http://localhost:8000/health/db

Check Redis connectivity:

http://localhost:8000/health/redis

Expected healthy responses:

GET /health
{"status":"healthy"}

GET /health/db
{"status":"healthy","database":"connected"}

GET /health/redis
{"status":"healthy","redis":"connected"}

Docker Logs

View API logs:

docker compose logs api

View worker logs:

docker compose logs worker

View PostgreSQL logs:

docker compose logs postgres

View Redis logs:

docker compose logs redis

Follow worker logs:

docker compose logs -f worker

PostgreSQL

Local PostgreSQL

Connect to PostgreSQL:

psql -U postgres

Connect to ComputeGrid:

\c computegrid

Check jobs table:

\d jobs

View jobs:

SELECT * FROM jobs;

Docker PostgreSQL

The Docker Compose PostgreSQL service uses:

Database:

computegrid

User:

postgres

Port inside Docker network:

5432

The service is reachable by other Compose services using:

postgres

Redis

Local Redis

Check Docker containers:

docker ps

Existing local Redis Stack container:

computegrid-redis-stack

Start Redis Stack if required:

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

Docker Compose Redis

The Compose Redis service is named:

redis

Internal port:

6379

The application connects using:

REDIS_HOST=redis

and:

REDIS_PORT=6379

Testing

Run the complete test suite:

pytest -v

Current verified result:

117 passed, 2 warnings

The tests cover:

health endpoints

database endpoint

Redis endpoint

job creation

job retrieval

request validation

scientific computation

workload dispatching

Redis queue behavior

stale recovery

retry behavior

atomic job claiming

worker processing

worker failure handling

lifecycle logging

performance timing instrumentation

CI

GitHub Actions workflow:

.github/workflows/ci.yml

CI currently verifies:

Python environment

PostgreSQL service

dependency installation

database initialization

automated tests

Current Task

Day 14 — Performance, Observability & Dockerization/Integration completed.

Verified:

Performance baseline instrumentation

Structured job lifecycle logging

Dockerfile

.dockerignore

Docker Compose environment

PostgreSQL container

Redis container

FastAPI container

Worker container

Docker health checks

API health endpoints

PostgreSQL connectivity

Redis connectivity

End-to-end Dockerized job processing

117 automated tests passing

Next Tasks

Day 15 — Final Cleanup, Documentation & Project Review

Planned focus:

Review the complete ComputeGrid architecture.

Review Docker configuration.

Complete README documentation.

Review COMPUTEGRID_PROGRESS.md.

Remove unnecessary development artifacts if any remain.

Review logging quality.

Review test coverage and remaining warnings.

Review error-handling and reliability behavior.

Review Git history and repository cleanliness.

Perform final end-to-end validation.

Prepare the project for portfolio/resume presentation.

Upcoming UI Integration

After the core backend and distributed execution architecture is stable, add a simple user-facing interface for submitting structured scientific workloads.

Initial UI workload choices:

Matrix Statistics

User selects:

Matrix Statistics

Input:

Matrix Size

Example:

1000

Backend generates and analyzes the matrix.

Expected result fields:

shape

mean

standard deviation

minimum

maximum

sum

Matrix Multiplication

User selects:

Matrix Multiplication

Potential structured inputs include:

matrix size

iterations

The UI should submit these parameters to the existing /jobs API rather than implementing computation itself.

The UI should remain a client of the existing ComputeGrid architecture:

UI
 ↓
FastAPI
 ↓
PostgreSQL
 ↓
Redis
 ↓
Worker
 ↓
Scientific Computation
 ↓
PostgreSQL
 ↓
UI

The UI should not bypass the job queue or execute scientific computation directly in the frontend.

Future Tasks

Final cleanup

Complete README documentation

Final architecture review

UI integration

Additional scientific workloads

Performance/load testing

Additional distributed-system reliability mechanisms

Possible transactional outbox/coordination mechanism

Production-oriented deployment improvements

Final project presentation and resume preparation

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

Atomic PostgreSQL job claiming is used to prevent duplicate worker execution.

Retry behavior is bounded by MAX_RETRIES = 3.

Stale running jobs can be recovered and requeued.

Docker Compose provides a reproducible local multi-service environment.

The API and worker use the same Docker image with different startup commands.

Docker service names are used for internal PostgreSQL and Redis connectivity.

Known Future Improvements

More scientific job types and computation dispatching.

User-facing UI for structured workload submission.

Performance and load testing with larger workloads.

Improved production observability.

Database migrations using a dedicated migration system such as Alembic for production-oriented deployments.

Additional distributed-system reliability mechanisms.

Transactional outbox or coordination mechanism for stronger PostgreSQL/Redis consistency guarantees.

Production deployment configuration.

Horizontal worker scaling and workload distribution improvements.

Known Issues

Two non-blocking upstream dependency deprecation warnings during test runs:

Starlette TestClient / httpx

AnyIO BlockingPortal

These warnings do not currently cause test failures.

The Docker Compose PostgreSQL credentials are intended for the local development environment and should not be treated as production secrets.

The current FastAPI startup uses SQLAlchemy create_all() for convenient local Docker database initialization. A production deployment should use a dedicated database migration workflow.

Git Status

Day 13 commit:

790f58e — Add automated test suite and CI

Day 14 changes were committed and pushed in commit 247ea9e (Complete Day 14 observability and Docker integration).

Before the Day 14 commit:

Full test suite must pass.

Docker Compose stack must be verified.

Final documentation must be reviewed.

Git diff must be reviewed.

After review, Day 14 changes should be committed and pushed to origin/main.