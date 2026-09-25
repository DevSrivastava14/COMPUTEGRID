from app.redis_client import redis_client

JOB_QUEUE_KEY = "computegrid:jobs"


def enqueue_job(job_id: int) -> int:
    """Enqueue a job ID at the tail of the Redis queue."""
    return redis_client.rpush(JOB_QUEUE_KEY, str(job_id))


def dequeue_job() -> int | None:
    """Dequeue a job ID from the head of the Redis queue (FIFO)."""
    item = redis_client.lpop(JOB_QUEUE_KEY)
    if item is not None:
        return int(item)
    return None
