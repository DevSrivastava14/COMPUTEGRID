from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    job_type: str
    input_data: Optional[dict[str, Any]] = None


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: int
    status: str
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
