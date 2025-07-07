from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime

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

class BookRead(BookBase):
    id: int
    s3_key: Optional[str] = None
    user_id: int
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