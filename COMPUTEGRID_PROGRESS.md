# ComputeGrid Progress

## Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are stored persistently, queued, processed by workers, and their status/results are stored in PostgreSQL.

## Current Phase

Day 7 — Worker Process and Job Lifecycle

---

## Completed

### Day 1 — Foundation + PostgreSQL

* Created GitHub repository and Python virtual environment.
* Set up FastAPI/Uvicorn and `/health` + Swagger `/docs`.
* Installed and configured PostgreSQL.
* Created `computegrid` database and `jobs` table.
* `jobs` contains:
  * `id`
  * `job_type`
  * `status`
  * `input_data` JSONB
  * `result` JSONB
  * `error_message`
  * `created_at`
  * `started_at`
  * `completed_at`
* Default job status is `queued`.

### Day 2 — FastAPI → PostgreSQL

* Added SQLAlchemy 2.x + Psycopg 3.
* Added `pydantic-settings`.
* Created `app/config.py` and `.env` / `.env.example`.
* Created `app/database.py`.
* Added SQLAlchemy engine, `SessionLocal`, and FastAPI `get_db()`.
* Added `/health/db`.
* Verified FastAPI ↔ PostgreSQL connection.

### Day 3 — Job Model + Schemas

* Created `app/models.py` with SQLAlchemy `Job` model mapped to existing `jobs` table.
* Created `app/schemas.py`:
  * `JobBase`
  * `JobCreate`
  * `JobResponse`
* `JobResponse` uses Pydantic `from_attributes=True`.
* Verified ORM queries and Pydantic serialization.

### Day 4 — Job Creation API

* Created `app/routers/jobs.py`.
* Registered `/jobs` router.
* Implemented `POST /jobs`.
* Uses `JobCreate`, `JobResponse`, and `get_db()`.
* New jobs are committed/refreshed in PostgreSQL.
* Returns HTTP `201`.
* New jobs start with `queued` status.

### Day 5 — Job Status API

* Implemented `GET /jobs/{job_id}`.
* Uses PostgreSQL/SQLAlchemy lookup.
* Returns `JobResponse`.
* Returns `404` when job does not exist.
* Job retrieval remains PostgreSQL-backed.

### Day 6 — Redis Job Queue

* Added `redis>=5.0.0` (installed version 8.1.0).
* Added `REDIS_HOST` and `REDIS_PORT` settings.
* Created `app/redis_client.py`.
* Added `/health/redis`.
* Created `app/queue.py`.
* Redis queue key: `computegrid:jobs`.
* Queue stores **only integer job IDs**.
* `RPUSH` + `LPOP` provides FIFO behavior.
* `POST /jobs` now:
  1. Commits job to PostgreSQL.
  2. Refreshes job.
  3. Enqueues job ID into Redis.
  4. Returns `JobResponse`.
* PostgreSQL remains the permanent source of truth.
* Redis is only the temporary job queue.
* Redis runs through Docker container `computegrid-redis-stack`.

### Day 7 — Worker

Created `app/worker.py`.

Worker currently:

1. Polls Redis using `dequeue_job()`.
2. Receives a job ID.
3. Creates its own `SessionLocal()` database session.
4. Looks up the job using `db.get(Job, job_id)`.
5. Verifies the job exists and is still `queued`.
6. Changes status:
   `queued → running`
7. Sets `started_at` using timezone-aware UTC time.
8. Commits the status change to PostgreSQL.
9. Closes the database session safely.
10. Sleeps when the queue is empty.

Worker is started with:

```bash
python -m app.worker

Verified successfully with a newly created job.

Current Implemented Lifecycle
QUEUED → RUNNING

Not yet implemented:

RUNNING → COMPLETED
RUNNING → FAILED

Scientific computation has not been implemented yet.

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
   ↓
PostgreSQL
(result/status)
Job Creation
POST /jobs
   ↓
Pydantic validation
   ↓
SQLAlchemy Job
   ↓
PostgreSQL commit + refresh
   ↓
Redis enqueue (job ID only)
   ↓
201 JobResponse
Worker
Redis LPOP
   ↓
job_id
   ↓
PostgreSQL lookup
   ↓
validate queued
   ↓
queued → running
   ↓
started_at
   ↓
PostgreSQL commit
   ↓
scientific computation
Important Architecture Decisions
PostgreSQL is the permanent source of truth.
Redis only stores job IDs, not complete job data.
Redis queue is computegrid:jobs.
Queue uses RPUSH + LPOP for FIFO behavior.
Job is committed to PostgreSQL before Redis enqueue.
Workers are independent processes, not FastAPI request handlers.
Workers use SessionLocal() directly; they do not use FastAPI's get_db().
Worker database sessions must always be closed.
Worker only changes queued → running after validating current status.
started_at records when worker processing begins.
Scientific computation will happen in workers, not inside the API request.
NumPy/Pandas are planned for scientific workloads.
Docker is used for Redis.
Known Issues / Future Reliability Concerns

These are known architectural limitations but are not being fixed yet:

Jobs created before Redis integration were never added to Redis.
Therefore old PostgreSQL queued jobs may not be processed.
PostgreSQL commit can succeed while Redis enqueue fails.
No retry/requeue mechanism yet.
No worker crash recovery yet.
No handling for jobs stuck in running.
Multiple-worker reliability/concurrency is not implemented yet.

These should be considered later when improving the distributed-system reliability.

Next Tasks
Day 8 — Scientific Job Execution
Define the first scientific job type and input contract.
Create an isolated computation function/module.
Use NumPy for the initial workload.
Connect worker to the computation.
Execute computation after queued → running.
Store the result in PostgreSQL JSONB.
Following Days
Implement running → completed.
Set completed_at.
Implement computation error handling.
Store errors in error_message.
Implement running → failed.
Test successful and failed jobs through GET /jobs/{job_id}.
Test the complete lifecycle.
Later
Multiple workers/concurrent execution.
Retry and failure recovery.
Queue reliability improvements.
Logging/observability.
Dockerize complete system.
Automated tests.
GitHub Actions CI/CD.
Performance/benchmarking.
Project Structure

Important current files:

app/
├── main.py
├── config.py
├── database.py
├── models.py
├── schemas.py
├── redis_client.py
├── queue.py
├── worker.py
└── routers/
    ├── __init__.py
    └── jobs.py

Important infrastructure:

PostgreSQL
  database: computegrid
  table: jobs

Redis
  container: computegrid-redis-stack
  port: 6379
  queue: computegrid:jobs
Useful Commands
Start API
uvicorn app.main:app --reload
Start Worker
python -m app.worker
Redis CLI
docker exec -it computegrid-redis-stack redis-cli

Check queue:

LRANGE computegrid:jobs 0 -1

Check queue length:

LLEN computegrid:jobs
PostgreSQL
psql -U postgres
\c computegrid

View jobs:

SELECT * FROM jobs;