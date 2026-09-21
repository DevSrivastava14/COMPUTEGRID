# ComputeGrid Progress

## Project Goal

ComputeGrid is a distributed scientific computing platform where users
submit computational jobs through an API. Jobs are queued, processed by
workers, and their status/results are stored persistently.

## Current Phase

Day 2 — FastAPI → PostgreSQL Integration

## Completed

### Day 1 — Project Foundation and Database Foundation

#### Project Setup
- Created GitHub repository
- Cloned repository locally
- Created Python virtual environment
- Installed FastAPI and Uvicorn
- Created initial FastAPI application
- Created `/health` endpoint
- Verified local FastAPI server
- Verified FastAPI Swagger documentation at `/docs`

#### PostgreSQL Setup
- Installed PostgreSQL
- Added PostgreSQL `bin` directory to Windows PATH
- Verified `psql` CLI
- Verified PostgreSQL server using `pg_isready`
- Created `computegrid` database
- Connected to `computegrid` using psql

#### Database Design
- Designed initial `jobs` table
- Created `jobs` table
- Added primary key with auto-generated identity
- Added job type
- Added job status
- Added JSONB input data
- Added JSONB result
- Added error message field
- Added job timestamps

#### Database Testing
- Successfully inserted first test job
- Verified job appears in PostgreSQL
- Verified default job status is `queued`

### Day 2 — FastAPI → PostgreSQL Integration

- Added SQLAlchemy 2.x and Psycopg 3 dependencies.
- Added pydantic-settings configuration.
- Created app/config.py.
- Created local .env configuration and .env.example.
- Confirmed .env is Git-ignored.
- Created app/database.py.
- Created SQLAlchemy engine using PostgreSQL + Psycopg.
- Created SessionLocal.
- Created get_db() FastAPI database session dependency.
- Verified a real SELECT 1 query against the computegrid database.
- Integrated get_db() with FastAPI.
- Preserved GET /health.
- Added GET /health/db.
- Verified both endpoints return HTTP 200.
- Verified FastAPI can obtain a live PostgreSQL session through dependency injection.

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

computegrid

Table:

jobs

Initial job lifecycle:

QUEUED → RUNNING → COMPLETED

or

QUEUED → RUNNING → FAILED

## Current Task

Day 2 — FastAPI → PostgreSQL Integration completed.

## Next Tasks

1. Create Job model / schema (SQLAlchemy & Pydantic)
2. Create Job creation API
3. Create Job status API
4. Introduce Redis queue
5. Introduce worker process

## Important Decisions

- Python is the primary language.
- FastAPI provides the API layer.
- PostgreSQL stores persistent job information.
- Redis will handle job queueing.
- Workers will execute computational jobs.
- NumPy/Pandas will be used for scientific workloads.
- Docker will be introduced later.
- Redis is intentionally not being introduced until the basic API/database flow is working.

## Known Issues

None currently.

## Setup

Create and activate the virtual environment:

    python -m venv .venv

    .venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r requirements.txt

Run the application:

    uvicorn app.main:app --reload

Health endpoints:

    http://127.0.0.1:8000/health
    http://127.0.0.1:8000/health/db

API documentation:

    http://127.0.0.1:8000/docs

## PostgreSQL

Connect to PostgreSQL:

    psql -U postgres

Connect to ComputeGrid:

    \c computegrid

Check jobs table:

    \d jobs

View jobs:

    SELECT * FROM jobs;