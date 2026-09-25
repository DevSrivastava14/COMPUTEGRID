# ComputeGrid Progress

## Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are queued, processed by workers, and their status/results are stored persistently.

## Current Phase

Day 6 — Redis Job Queue Integration

## Completed

### Day 1 — Project Foundation and Database Foundation

#### Project Setup

* Created GitHub repository

* Cloned repository locally

* Created Python virtual environment

* Installed FastAPI and Uvicorn

* Created initial FastAPI application

* Created `/health` endpoint

* Verified local FastAPI server

* Verified FastAPI Swagger documentation at `/docs`

#### PostgreSQL Setup

* Installed PostgreSQL

* Added PostgreSQL `bin` directory to Windows PATH

* Verified `psql` CLI

* Verified PostgreSQL server using `pg_isready`

* Created `computegrid` database

* Connected to `computegrid` using psql

#### Database Design

* Designed initial `jobs` table

* Created `jobs` table

* Added primary key with auto-generated identity

* Added job type

* Added job status

* Added JSONB input data

* Added JSONB result

* Added error message field

* Added job timestamps

#### Database Testing

* Successfully inserted first test job

* Verified job appears in PostgreSQL

* Verified default job status is `queued`

### Day 2 — FastAPI → PostgreSQL Integration

* Added SQLAlchemy 2.x and Psycopg 3 dependencies.

* Added pydantic-settings configuration.

* Created `app/config.py`.

* Created local `.env` configuration and `.env.example`.

* Confirmed `.env` is Git-ignored.

* Created `app/database.py`.

* Created SQLAlchemy engine using PostgreSQL + Psycopg.

* Created `SessionLocal`.

* Created `get_db()` FastAPI database session dependency.

* Verified a real `SELECT 1` query against the `computegrid` database.

* Integrated `get_db()` with FastAPI.

* Preserved `GET /health`.

* Added `GET /health/db`.

* Verified both endpoints return HTTP 200.

* Verified FastAPI can obtain a live PostgreSQL session through dependency injection.

### Day 3 — Job Model and Pydantic Schemas

* Inspected existing `jobs` table schema in PostgreSQL without modifying or altering database structure.

* Created `app/models.py` with the SQLAlchemy `Job` ORM model mapped accurately to the existing `jobs` table using SQLAlchemy 2.0 type annotations (`Mapped`, `mapped_column`, `Identity`, `JSONB`, `DateTime(timezone=True)`).

* Created `app/schemas.py` with Pydantic v2 schemas (`JobBase`, `JobCreate`, `JobResponse`).

* Configured `JobResponse` with `model_config = ConfigDict(from_attributes=True)` for seamless ORM/object serialization.

* Verified SQLAlchemy recognition and registration of `Job` model on `Base.metadata`.

* Tested safe, read-only SELECT query against PostgreSQL `jobs` table using `Job` ORM model.

* Tested and validated Pydantic serialization of database records using `JobResponse.model_validate()`.

### Day 4 — Job Creation API

* Created `app/routers/__init__.py` as the API router package.

* Created `app/routers/jobs.py`.

* Created the `/jobs` FastAPI router with the `jobs` tag.

* Registered the jobs router in `app/main.py`.

* Implemented `POST /jobs`.

* Integrated the existing `JobCreate` Pydantic schema for request validation.

* Integrated the existing `JobResponse` Pydantic schema for response serialization.

* Integrated the existing `get_db()` database dependency.

* Created SQLAlchemy `Job` objects from validated API input.

* Added new jobs to the SQLAlchemy session.

* Committed new jobs to PostgreSQL.

* Refreshed the SQLAlchemy object after database commit to retrieve generated fields.

* Verified `POST /jobs` through FastAPI Swagger.

* Verified successful HTTP `201 Created` response.

* Verified the created job receives a database-generated ID.

* Verified the default job status is `queued`.

* Verified the created job exists in the PostgreSQL `jobs` table.

* Confirmed `result`, `error_message`, `started_at`, and `completed_at` are initially `null` for a newly created job.

### Day 5 — Job Status API

* Implemented `GET /jobs/{job_id}`.

* Used the existing SQLAlchemy `Job` ORM model and `get_db()` dependency.

* Added database lookup using the job ID.

* Returned the existing `JobResponse` schema for successful requests.

* Added HTTP `404 Not Found` handling when a requested job does not exist.

* Verified `GET /jobs/9999` returns HTTP `404` with `{"detail":"Job not found"}`.

* Verified `GET /jobs/3` returns HTTP `200` with the persisted job data.

* Confirmed job status and timestamps are correctly retrieved from PostgreSQL.

* Kept job retrieval synchronous and PostgreSQL-backed before introducing Redis and workers.

### Day 6 — Redis Job Queue Integration

* Added Python Redis client dependency (`redis>=5.0.0`, version 8.1.0 installed) to `requirements.txt`.

* Extended `Settings` in `app/config.py` with `REDIS_HOST` (default `localhost`) and `REDIS_PORT` (default `6379`), and updated `.env.example`.

* Created `app/redis_client.py` providing a reusable Redis client instance.

* Added `GET /health/redis` endpoint to `app/main.py` executing a live Redis PING with `RedisError` handling.

* Created `app/queue.py` with a Redis LIST queue abstraction using key `computegrid:jobs`:
  * `enqueue_job()` pushes job IDs to the tail using `RPUSH`.
  * `dequeue_job()` pops job IDs from the head using `LPOP` (FIFO).

* Integrated `POST /jobs` in `app/routers/jobs.py` with the Redis job queue:
  * PostgreSQL remains the persistent source of truth (committed and refreshed first).
  * Redis receives only the integer job ID.
  * Explicitly handles `RedisError` on enqueue failures.

* Verified full integration:
  * Successfully created and enqueued job ID 4 in live test.
  * Verified PostgreSQL record persistence.
  * Verified Redis key `computegrid:jobs` contained `['4']`.
  * Verified FIFO queue mechanics and cleaned test queue data.
  * Verified `GET /jobs/{job_id}`, `GET /health`, `GET /health/db`, and `GET /health/redis` return HTTP 200.

## Current Architecture

Client
↓
FastAPI
↓
PostgreSQL (persistent job record)
↓
Redis Queue (job ID)
↓
Worker
↓
Scientific Computation
↓
PostgreSQL (result/status)

Current job creation and queuing flow:

Client
↓
`POST /jobs`
↓
Pydantic validation (`JobCreate`)
↓
SQLAlchemy `Job`
↓
PostgreSQL Commit & Refresh (Source of Truth)
↓
Redis Enqueue (`computegrid:jobs` list, Job ID only)
↓
`JobResponse` (HTTP 201)

Current job status retrieval flow:

Client
↓
`GET /jobs/{job_id}`
↓
SQLAlchemy lookup by ID
↓
PostgreSQL
↓
`JobResponse` (HTTP 200)

Upcoming:

Worker Process
↓
Redis Dequeue (`LPOP computegrid:jobs`)
↓
PostgreSQL Job Lookup
↓
Status update: `queued` → `running`
↓
Scientific Computation
↓
Status update: `running` → `completed` / `failed`

## Current Database

Database:

`computegrid`

Table:

`jobs`

Initial job lifecycle:

`QUEUED → RUNNING → COMPLETED`

or

`QUEUED → RUNNING → FAILED`

Current behavior:

* Newly submitted jobs are stored in PostgreSQL with `queued` status and enqueued as IDs into Redis (`computegrid:jobs`).

* Individual jobs can be retrieved by their database ID through the API (`GET /jobs/{job_id}`).

* Worker execution and computational processing will be introduced in the next phase.

## Current Task

Day 6 — Redis Job Queue Integration completed.

## Next Tasks

1. Day 7 — Worker:
   * Introduce worker process
   * Dequeue job IDs from Redis (`computegrid:jobs`)
   * Look up job records in PostgreSQL
   * Transition job status: `queued` → `running`

2. Connect queued jobs to scientific computation

## Important Decisions

* Python is the primary language.

* FastAPI provides the API layer.

* PostgreSQL stores persistent job information and remains the permanent source of truth.

* Redis handles lightweight job queueing (storing only integer job IDs).

* Queue key is `computegrid:jobs` using a Redis LIST with FIFO semantics (`RPUSH` / `LPOP`).

* Workers will execute computational jobs asynchronously.

* NumPy/Pandas will be used for scientific workloads.

* Docker is used for services like Redis (`computegrid-redis-stack`).

* Job creation commits to PostgreSQL before enqueuing to Redis.

* Job status retrieval is handled synchronously through PostgreSQL.

## Known Issues

None currently.

## Setup

Create and activate the virtual environment:

```bash
python -m venv .venv

.venv\Scripts\Activate.ps1
```
Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn app.main:app --reload
```

Health endpoints:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/db
http://127.0.0.1:8000/health/redis
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## PostgreSQL

Connect to PostgreSQL:

```bash
psql -U postgres
```

Connect to ComputeGrid:

```sql
\c computegrid
```

Check jobs table:

```sql
\d jobs
```

View jobs:

```sql
SELECT * FROM jobs;
```
