from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from core.config import settings

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    data: Optional[Dict[str, Any]] = None
    s3_public_link: HttpUrl

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    data: Optional[Dict[str, Any]] = None

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    data: Optional[Dict[str, Any]] = None
    is_deleted: Optional[bool] = False

class BookProcessingJobInfo(BaseModel):
    id: int
    book_id: int
    user_id: int
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    processed_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BookRead(BookBase):
    id: int
    s3_key: Optional[str] = None
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    latest_processing_job: Optional[BookProcessingJobInfo] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Get the latest non-deleted processing job
        latest_job = None
        if hasattr(obj, 'processing_jobs') and obj.processing_jobs:
            latest_job = next(
                (job for job in sorted(
                    obj.processing_jobs,
                    key=lambda x: x.created_at,
                    reverse=True
                ) if not job.is_deleted),
                None
            )
        
        # Create a dict of the base attributes
        obj_dict = {
            "id": obj.id,
            "title": obj.title,
            "author": obj.author,
            "data": obj.data,
            "s3_key": obj.s3_key,
            "user_id": obj.user_id,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "s3_public_link": f"{settings.AWS_PUBLIC_URL}/{obj.s3_key}" if obj.s3_key else None,
            "latest_processing_job": BookProcessingJobInfo.from_orm(latest_job) if latest_job else None
        }
        return cls(**obj_dict)

class ProcessedBookData(BaseModel):
    """Schema for processed book data response"""
    book_id: int
    title: str
    author: str
    processing_status: str
    processed_data: Optional[Dict[str, Any]] = None
    processing_result: Optional[Dict[str, Any]] = None
    last_processing_job: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Project association schemas
class BookProjectAssociation(BaseModel):
    project_id: int = Field(..., gt=0)

class BookWithProjects(BookRead):
    project_ids: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Extract project IDs from the projects relationship if available
        if hasattr(self, 'projects') and self.projects:
            self.project_ids = [project.id for project in self.projects]
