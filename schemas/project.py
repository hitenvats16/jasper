from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from core.config import settings
from schemas.book import BookProcessingJobInfo

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class ProjectSortField(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"
    title = "title"
    book_count = "book_count"

class BookInProject(BaseModel):
    id: int
    title: str
    author: str
    s3_key: Optional[str] = None
    s3_public_link: Optional[str] = None
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
            "s3_key": obj.s3_key,
            "s3_public_link": f"{settings.AWS_PUBLIC_URL}/{obj.s3_key}" if obj.s3_key else None,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "latest_processing_job": BookProcessingJobInfo.from_orm(latest_job) if latest_job else None
        }
        return cls(**obj_dict)

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None

class ProjectCreate(ProjectBase):
    book_id: Optional[int] = None  # Optional book ID to associate with project

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None
    is_deleted: Optional[bool] = None
    book_id: Optional[int] = None  # Optional book ID to associate with project

class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str = None
    tags: List[str] = None
    data: Optional[dict] = None
    user_id: int
    books: List[BookInProject] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    book_count: int = 0

    class Config:
        from_attributes = True
    
    @classmethod
    def from_project(cls, project):
        if not project:
            return None
        return cls(
            id=project.id,
            title=project.title,
            description=project.description,
            tags=project.tags,
            data=project.data or None,
            user_id=project.user_id,
            books=[BookInProject.from_orm(book) for book in project.books],
            created_at=project.created_at,
            updated_at=project.updated_at,
            book_count=len(project.books) if project.books else 0
        )

class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int 