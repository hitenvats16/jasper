from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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

class ProjectRead(ProjectBase):
    id: int
    user_id: int
    book_ids: List[int] = []  # List of associated book IDs
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Extract book IDs from the books relationship if available
        if hasattr(self, 'books') and self.books:
            self.book_ids = [book.id for book in self.books] 