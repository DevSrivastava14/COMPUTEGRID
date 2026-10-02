"""
tests/conftest.py
=================
Pytest configuration and test fixtures foundation for ComputeGrid.
"""

from collections.abc import Generator
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.main import app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Provide an isolated SQLAlchemy database session connected to PostgreSQL.
    
    Compatible with PostgreSQL-specific model types (JSONB, Identity).
    Rolls back any uncommitted changes and closes the session after the test.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient with the database dependency overridden
    to use the test session fixture.
    """
    def _get_test_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Mock the Redis client for isolated unit and integration testing without
    requiring a live Redis connection.
    """
    mock = MagicMock()
    mock.ping.return_value = True
    mock.rpush.return_value = 1
    mock.lpop.return_value = None

    monkeypatch.setattr("app.redis_client.redis_client", mock)
    monkeypatch.setattr("app.queue.redis_client", mock)
    monkeypatch.setattr("app.main.redis_client", mock)
    return mock
