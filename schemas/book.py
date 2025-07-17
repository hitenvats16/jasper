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

class BookSortField(str, Enum):
    TITLE = "title"
    AUTHOR = "author"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    ESTIMATED_TOKENS = "estimated_tokens"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    data: Optional[Dict[str, Any]] = None
    s3_public_link: HttpUrl
    estimated_tokens: Optional[int] = Field(default=0, description="Estimated number of tokens in the book")

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
            "latest_processing_job": BookProcessingJobInfo.from_orm(latest_job) if latest_job else None,
            "estimated_tokens": obj.estimated_tokens if hasattr(obj, 'estimated_tokens') else 0
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
    estimated_tokens: Optional[int] = Field(default=0, description="Estimated number of tokens in the book")

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

class BookFilters(BaseModel):
    """Query parameters for filtering books"""
    search: Optional[str] = Field(None, description="Search term for title or author")
    min_tokens: Optional[int] = Field(None, ge=0, description="Minimum number of tokens")
    max_tokens: Optional[int] = Field(None, ge=0, description="Maximum number of tokens")
    has_processing_job: Optional[bool] = Field(None, description="Filter books with processing jobs")
    processing_status: Optional[JobStatus] = Field(None, description="Filter by processing job status")
    project_id: Optional[int] = Field(None, description="Filter books by project")
    sort_by: Optional[BookSortField] = Field(BookSortField.CREATED_AT, description="Field to sort by")
    sort_order: Optional[SortOrder] = Field(SortOrder.DESC, description="Sort order (asc/desc)")
    page: Optional[int] = Field(1, ge=1, description="Page number")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="Items per page")

class BookListResponse(BaseModel):
    """Response model for paginated book list"""
    items: List[BookRead]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True