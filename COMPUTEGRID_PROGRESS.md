# ComputeGrid Progress

## Project Goal

ComputeGrid is a distributed scientific computing platform where users
submit computational jobs through an API. Jobs are queued, processed by
workers, and their status/results are stored persistently.

## Current Phase

Day 1 — Project Foundation and Database Foundation

## Completed

### Project Setup
- Created GitHub repository
- Cloned repository locally
- Created Python virtual environment
- Installed FastAPI and Uvicorn
- Created initial FastAPI application
- Created `/health` endpoint
- Verified local FastAPI server
- Verified FastAPI Swagger documentation at `/docs`

### PostgreSQL Setup
- Installed PostgreSQL
- Added PostgreSQL `bin` directory to Windows PATH
- Verified `psql` CLI
- Verified PostgreSQL server using `pg_isready`
- Created `computegrid` database
- Connected to `computegrid` using psql

### Database Design
- Designed initial `jobs` table
- Created `jobs` table
- Added primary key with auto-generated identity
- Added job type
- Added job status
- Added JSONB input data
- Added JSONB result
- Added error message field
- Added job timestamps

### Database Testing
- Successfully inserted first test job
- Verified job appears in PostgreSQL
- Verified default job status is `queued`

## Current Architecture

Client
  ↓
FastAPI
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

Day 1 — Foundation completed.

## Next Tasks

1. Connect FastAPI to PostgreSQL
2. Create database connection layer
3. Create job model/schema
4. Create job creation API
5. Create job status API
6. Introduce Redis queue
7. Introduce worker process

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

Health endpoint:

    http://127.0.0.1:8000/health

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