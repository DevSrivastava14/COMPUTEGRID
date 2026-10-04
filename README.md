# ComputeGrid

A distributed scientific computing platform built with FastAPI, PostgreSQL, and Redis. Users submit computational jobs through a REST API; jobs are queued in Redis, claimed atomically by worker processes, executed as NumPy workloads, and their results are persisted in PostgreSQL.

---

## Key Features

- **REST API** — Submit and query jobs via HTTP
- **Persistent job storage** — PostgreSQL is the authoritative source of truth for all job state
- **Redis queue** — Lightweight, fast job dispatching using a FIFO list
- **Background worker** — Independent worker process consumes the queue and runs scientific computation
- **Atomic job claiming** — Conditional `UPDATE … WHERE status = 'queued'` prevents duplicate execution across concurrent workers
- **Automatic retries** — Failed jobs are re-queued up to `MAX_RETRIES = 3` times before transitioning to `failed`
- **Stale-job recovery** — Jobs stuck in `running` beyond 10 minutes can be detected and re-queued
- **Docker Compose** — One command brings up the full four-service stack
- **CI** — GitHub Actions runs the full test suite on every push and pull request to `main`

---

## Architecture

```
Client
  │
  ▼
FastAPI (port 8000)
  │   POST /jobs → persists job to PostgreSQL → enqueues job ID to Redis
  │   GET  /jobs/{id} → reads job status/result from PostgreSQL
  │
  ├── PostgreSQL  ← source of truth for all job state
  │
  └── Redis       ← queue of pending job IDs ("computegrid:jobs")
                        │
                        ▼
                  Worker process
                    │  LPOP job ID from Redis
                    │  Atomic claim: UPDATE jobs SET status='running' WHERE status='queued'
                    │  Execute scientific computation (NumPy)
                    │  Write result / error back to PostgreSQL
                    └─ Retry or mark failed
```

Multiple worker processes can run concurrently. Atomic claiming in PostgreSQL ensures each job is processed exactly once.

---

## Technology Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.141 + Uvicorn |
| Database | PostgreSQL 16 (SQLAlchemy 2.x, Psycopg 3) |
| Queue | Redis 7 |
| Configuration | pydantic-settings |
| Scientific computation | NumPy |
| Testing | pytest, httpx, FastAPI TestClient |
| Containerisation | Docker, Docker Compose |
| CI | GitHub Actions |
| Language | Python 3.13 |

---

## Scientific Workloads

Jobs are dispatched by `job_type`. Three workloads are currently implemented in `app/compute.py`:

### `matrix_stats`

Generates a random NxN matrix and computes summary statistics.

| Input | Type | Default |
|---|---|---|
| `size` | int | 100 |

Result fields: `shape`, `mean`, `std`, `min`, `max`, `sum`

### `matrix_multiply`

Multiplies two random NxN matrices using `numpy.matmul`.

| Input | Type | Default |
|---|---|---|
| `size` | int | 100 |

Result fields: `shape`, `mean`, `std`, `min`, `max`

### `data_stats`

Generates a random 1D dataset and computes descriptive statistics.

| Input | Type | Default |
|---|---|---|
| `size` | int | 1000 |

Result fields: `size`, `mean`, `std`, `min`, `max`, `sum`, `median`

---

## Job Lifecycle

```
POST /jobs
  └─ Job inserted into PostgreSQL (status: queued)
  └─ Job ID pushed to Redis queue (RPUSH)

Worker (running independently)
  └─ Polls Redis every 2 s (LPOP)
  └─ Atomically claims job in PostgreSQL (queued → running)
  └─ Runs scientific computation
  └─ On success:  status → completed, result written to PostgreSQL
  └─ On failure:  retry_count++, re-enqueued (up to 3 retries)
                  after 3 failures: status → failed

GET /jobs/{id}
  └─ Returns current status, result, error, and timestamps from PostgreSQL
```

### Job Statuses

| Status | Meaning |
|---|---|
| `queued` | Waiting in the Redis queue |
| `running` | Claimed by a worker, computation in progress |
| `completed` | Computation finished successfully |
| `failed` | Exceeded maximum retries |

---

## Reliability

**Atomic job claiming** — The worker uses a conditional SQL `UPDATE` (`WHERE status = 'queued'`) as the claim operation. If two workers race on the same job, only one will see `rowcount == 1`; the other skips it cleanly.

**Bounded retries** — On computation failure, `retry_count` is incremented and the job is re-enqueued. After `MAX_RETRIES = 3` attempts, the job transitions permanently to `failed` and is not re-queued.

**Stale-job recovery** — `app/recovery.py` exposes `find_stale_jobs()` and `recover_stale_job()`. A job is considered stale when it has been `running` for more than 10 minutes without a `completed_at` timestamp — typically the result of a crashed worker. Recovery resets the job to `queued` and re-enqueues it.

---

## Docker Compose Setup

> **Prerequisites:** Docker and Docker Compose installed.

```bash
# Start the full stack (PostgreSQL + Redis + API + Worker)
docker compose up --build

# API is available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs

# Stop and remove containers
docker compose down

# Stop and also remove the persistent PostgreSQL volume
docker compose down -v
```

The `api` and `worker` services share the same Docker image. The worker is started by overriding the default command with `python -m app.worker`.

---

## Local Development Setup

> **Prerequisites:** Python 3.13, PostgreSQL running locally, Redis running locally.

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd COMPUTEGRID

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and set DB_PASSWORD to your local PostgreSQL password

# 5. Create the database schema
python -c "from app.database import Base, engine; from app.models import Job; Base.metadata.create_all(engine)"

# 6. Start the API server
uvicorn app.main:app --reload

# 7. Start a worker (separate terminal, venv activated)
python -m app.worker
```

---

## API Reference

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Basic liveness check |
| `GET` | `/health/db` | Verifies PostgreSQL connectivity |
| `GET` | `/health/redis` | Verifies Redis connectivity |

### Jobs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/jobs` | Submit a new job |
| `GET` | `/jobs/{job_id}` | Retrieve job status and result |

Interactive documentation: **http://localhost:8000/docs**

### Example: Submit a job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "matrix_stats", "input_data": {"size": 500}}'
```

Response (`201 Created`):

```json
{
  "id": 1,
  "job_type": "matrix_stats",
  "status": "queued",
  "input_data": {"size": 500},
  "result": null,
  "error_message": null,
  "created_at": "2026-10-04T14:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

### Example: Poll for results

```bash
curl http://localhost:8000/jobs/1
```

Response (after the worker completes the job):

```json
{
  "id": 1,
  "job_type": "matrix_stats",
  "status": "completed",
  "input_data": {"size": 500},
  "result": {
    "shape": [500, 500],
    "mean": 0.499987,
    "std": 0.288654,
    "min": 0.000032,
    "max": 0.999981,
    "sum": 124996.75
  },
  "error_message": null,
  "created_at": "2026-10-04T14:00:00Z",
  "started_at": "2026-10-04T14:00:01Z",
  "completed_at": "2026-10-04T14:00:01Z"
}
```

---

## Running Tests

Tests require a running PostgreSQL instance. Redis is mocked in all tests.

```bash
# Run the full test suite with verbose output
pytest -v
```

The test suite currently contains **117 tests** across four files:

| File | Scope |
|---|---|
| `tests/test_api.py` | API endpoint integration tests |
| `tests/test_compute.py` | Scientific computation unit tests |
| `tests/test_worker.py` | Worker lifecycle and retry logic tests |
| `tests/test_queue_recovery.py` | Queue operations and stale-job recovery tests |

CI runs the full suite automatically on every push and pull request to `main` via GitHub Actions (`.github/workflows/ci.yml`).

---

## Project Structure

```
COMPUTEGRID/
├── app/
│   ├── main.py           # FastAPI app, lifespan, health endpoints
│   ├── config.py         # pydantic-settings configuration
│   ├── database.py       # SQLAlchemy engine, session factory, get_db()
│   ├── models.py         # Job ORM model
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── redis_client.py   # Redis client singleton
│   ├── queue.py          # enqueue_job() / dequeue_job()
│   ├── compute.py        # Scientific workloads and dispatch table
│   ├── recovery.py       # Stale-job detection and recovery
│   ├── worker.py         # Worker process: poll → claim → compute → persist
│   └── routers/
│       └── jobs.py       # POST /jobs, GET /jobs/{id}
├── tests/
│   ├── conftest.py       # db_session, client, mock_redis fixtures
│   ├── test_api.py
│   ├── test_compute.py
│   ├── test_worker.py
│   └── test_queue_recovery.py
├── .github/
│   └── workflows/
│       └── ci.yml        # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Future Improvements

- **Database migrations** — Replace `create_all()` startup with Alembic for production-safe schema management
- **Additional workloads** — Expand the scientific compute dispatch table with more job types
- **UI** — A simple web interface for submitting structured workloads and polling results
- **Production deployment** — Secrets management, non-root Docker user, reverse proxy, TLS
- **Horizontal scaling** — Workload-aware distribution across multiple worker processes or machines
- **Observability** — Structured logging, metrics, distributed tracing
- **Transactional outbox** — Stronger PostgreSQL/Redis consistency guarantees to eliminate the window between DB commit and Redis enqueue
