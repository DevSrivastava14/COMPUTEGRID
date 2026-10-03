"""
tests/test_api.py
=================
API-level tests for ComputeGrid endpoints.

Coverage:
  - GET  /health
  - GET  /health/db
  - GET  /health/redis
  - POST /jobs
  - GET  /jobs/{job_id}
"""

import logging
import pytest
from redis.exceptions import RedisError
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# GET /health/db
# ---------------------------------------------------------------------------


class TestHealthDbEndpoint:
    def test_health_db_returns_200(self, client: TestClient):
        response = client.get("/health/db")
        assert response.status_code == 200

    def test_health_db_response_structure(self, client: TestClient):
        response = client.get("/health/db")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# GET /health/redis
# ---------------------------------------------------------------------------


class TestHealthRedisEndpoint:
    def test_health_redis_success(self, client: TestClient, mock_redis):
        """Returns 200 and correct body when Redis ping succeeds."""
        response = client.get("/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"] == "connected"

    def test_health_redis_unavailable_returns_503(self, client: TestClient, mock_redis):
        """Returns 503 when Redis raises RedisError."""
        mock_redis.ping.side_effect = RedisError("connection refused")
        response = client.get("/health/redis")
        assert response.status_code == 503
        assert response.json()["detail"] == "Redis is unreachable"


# ---------------------------------------------------------------------------
# POST /jobs
# ---------------------------------------------------------------------------


class TestCreateJobEndpoint:
    _valid_payload = {"job_type": "matrix_multiply", "input_data": {"size": 128}}

    def test_create_job_returns_201(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json=self._valid_payload)
        assert response.status_code == 201

    def test_create_job_response_contains_job(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json=self._valid_payload)
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_job_initial_status_is_queued(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json=self._valid_payload)
        assert response.json()["status"] == "queued"

    def test_create_job_preserves_job_type(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json=self._valid_payload)
        assert response.json()["job_type"] == self._valid_payload["job_type"]

    def test_create_job_preserves_input_data(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json=self._valid_payload)
        assert response.json()["input_data"] == self._valid_payload["input_data"]

    def test_create_job_calls_enqueue_with_job_id(self, client: TestClient, mock_redis):
        """enqueue_job (via redis_client.rpush) must be called with the new job ID."""
        response = client.post("/jobs", json=self._valid_payload)
        created_id = str(response.json()["id"])
        mock_redis.rpush.assert_called_once()
        _key, queued_id = mock_redis.rpush.call_args.args
        assert queued_id == created_id

    def test_create_job_without_input_data(self, client: TestClient, mock_redis):
        """input_data is optional; omitting it should still return 201."""
        response = client.post("/jobs", json={"job_type": "ping"})
        assert response.status_code == 201
        assert response.json()["input_data"] is None

    def test_create_job_redis_error_returns_500(self, client: TestClient, mock_redis):
        """If enqueue fails, the endpoint must return 500."""
        mock_redis.rpush.side_effect = RedisError("queue unavailable")
        response = client.post("/jobs", json=self._valid_payload)
        assert response.status_code == 500
        assert "enqueue" in response.json()["detail"].lower()

    def test_create_job_logs_submission_latency(self, client: TestClient, mock_redis, caplog: pytest.LogCaptureFixture):
        """Job submission should log execution latency with job_id and job_type."""
        with caplog.at_level(logging.INFO):
            response = client.post("/jobs", json=self._valid_payload)
        assert response.status_code == 201
        job_id = response.json()["id"]
        assert any(
            f"job_id={job_id}" in record.message
            and "job submission completed in" in record.message
            and "type=matrix_multiply" in record.message
            for record in caplog.records
        )


# ---------------------------------------------------------------------------
# POST /jobs – schema validation
# ---------------------------------------------------------------------------


class TestCreateJobValidation:
    def test_missing_job_type_returns_422(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json={"input_data": {"x": 1}})
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient, mock_redis):
        response = client.post("/jobs", json={})
        assert response.status_code == 422

    def test_non_string_job_type_returns_422(self, client: TestClient, mock_redis):
        """job_type must be a string; sending an integer should fail validation."""
        response = client.post("/jobs", json={"job_type": 42})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------


class TestGetJobEndpoint:
    def test_get_existing_job_returns_200(self, client: TestClient, mock_redis):
        create_resp = client.post(
            "/jobs",
            json={"job_type": "sort", "input_data": {"items": [3, 1, 2]}},
        )
        assert create_resp.status_code == 201
        job_id = create_resp.json()["id"]

        response = client.get(f"/jobs/{job_id}")
        assert response.status_code == 200

    def test_get_existing_job_response_fields(self, client: TestClient, mock_redis):
        create_resp = client.post(
            "/jobs",
            json={"job_type": "sort", "input_data": {"items": [3, 1, 2]}},
        )
        job_id = create_resp.json()["id"]

        data = client.get(f"/jobs/{job_id}").json()
        assert data["id"] == job_id
        assert data["job_type"] == "sort"
        assert data["status"] == "queued"
        assert data["input_data"] == {"items": [3, 1, 2]}
        assert "created_at" in data

    def test_get_nonexistent_job_returns_404(self, client: TestClient, mock_redis):
        response = client.get("/jobs/999999999")
        assert response.status_code == 404

    def test_get_nonexistent_job_error_detail(self, client: TestClient, mock_redis):
        response = client.get("/jobs/999999999")
        assert response.json()["detail"] == "Job not found"
