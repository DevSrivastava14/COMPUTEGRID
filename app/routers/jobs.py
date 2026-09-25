from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
from app.queue import enqueue_job
from app.schemas import JobCreate, JobResponse

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    job = Job(
        job_type=job_in.job_type,
        input_data=job_in.input_data,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        enqueue_job(job.id)
    except RedisError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job created in database but failed to enqueue in Redis",
        )

    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job

