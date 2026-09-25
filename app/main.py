from fastapi import Depends, FastAPI, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.redis_client import redis_client
from app.routers import jobs

app = FastAPI(title="ComputeGrid")

app.include_router(jobs.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


@app.get("/health/redis")
def health_check_redis():
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unreachable",
        )
