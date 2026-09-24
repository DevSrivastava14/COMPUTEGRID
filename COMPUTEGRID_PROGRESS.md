# ComputeGrid Progress

## Project Goal

ComputeGrid is a distributed scientific computing platform where users submit computational jobs through an API. Jobs are queued, processed by workers, and their status/results are stored persistently.

## Current Phase

Day 5 — Job Status API

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

## Current Architecture

Client

↓

FastAPI

↓

SQLAlchemy/Psycopg

↓

PostgreSQL

↓

jobs table

Current job creation flow:

Client

↓

`POST /jobs`

↓

Pydantic validation

↓

SQLAlchemy `Job`

↓

PostgreSQL

↓

`JobResponse`

Current job status retrieval flow:

Client

↓

`GET /jobs/{job_id}`

↓

SQLAlchemy `Job`

↓

PostgreSQL

↓

`JobResponse`

Upcoming:

FastAPI

↓

PostgreSQL

↓

Redis Queue

↓

Worker

↓

Scientific Computation

↓

PostgreSQL

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

* Newly submitted jobs are stored with `queued` status.

* Jobs are currently persisted but not yet processed by workers.

* Individual jobs can now be retrieved by their database ID through the API.

* Redis queueing and worker processing will be introduced in later phases.

## Current Task

Day 5 — Job Status API completed.

## Next Tasks

1. Day 6 — Introduce Redis queue

2. Introduce worker process

3. Connect queued jobs to scientific computation

## Important Decisions

* Python is the primary language.

* FastAPI provides the API layer.

* PostgreSQL stores persistent job information.

* Redis will handle job queueing.

* Workers will execute computational jobs.

* NumPy/Pandas will be used for scientific workloads.

* Docker will be introduced later.

* Redis is intentionally not being introduced until the basic API/database flow is working.

* Job creation is handled synchronously by the API and persisted to PostgreSQL before Redis is introduced.

* Job status retrieval is handled synchronously through PostgreSQL before Redis and worker processing are introduced.

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
