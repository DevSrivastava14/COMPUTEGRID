ComputeGrid Progress

Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are queued, processed by workers, and their status/results are stored persistently.

Current Phase

Day 8 — Scientific Computation, Job Completion and Failure Handling

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

Current Architecture

Client

↓

FastAPI

↓

PostgreSQL

(source of truth)

↓

Redis Queue

(computegrid)

↓

Worker

↓

Scientific Computation

(NumPy)

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

├──→ COMPLETED
│     ├── result
│     └── completed_at
│
└──→ FAILED
└── error_message

Current Database

Database:

computegrid

Table:

jobs

Important fields:

id

job_type

status

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

Day 8 — Scientific Computation, Completion and Failure Handling completed.

Next Tasks

Day 9 — Continue the existing ComputeGrid roadmap.

Review and commit all Day 8 changes.

Push Day 8 changes to GitHub.

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

Retry/requeue mechanisms.

Worker crash recovery.

Handling jobs stuck in running.

Multiple-worker concurrency and reliability.

More job types and computation dispatching.

Automated tests.

Improved logging and observability.

Dockerizing the complete application.

GitHub Actions CI/CD.

Performance and load testing.

Additional distributed-system reliability mechanisms.

Known Issues

No blocking issues identified in the Day 8 implementation.

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

LRANGE computegrid 0 -1

Check queue length:

LLEN computegrid

Exit:

exit