import logging
from app.redis_client import redis_client

logger = logging.getLogger(__name__)

JOB_QUEUE_KEY = "computegrid:jobs"


def enqueue_job(job_id: int) -> int:
    """Enqueue a job ID at the tail of the Redis queue."""
    logger.info("job_id=%d | enqueued to Redis queue '%s'", job_id, JOB_QUEUE_KEY)
    return redis_client.rpush(JOB_QUEUE_KEY, str(job_id))


def dequeue_job() -> int | None:
    """Dequeue a job ID from the head of the Redis queue (FIFO)."""
    item = redis_client.lpop(JOB_QUEUE_KEY)
    if item is not None:
        job_id = int(item)
        logger.info("job_id=%d | dequeued from Redis queue '%s'", job_id, JOB_QUEUE_KEY)
        return job_id
    return None
