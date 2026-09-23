from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
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
    return job
