from sqlalchemy.orm import Session
from models.project import Project
from models.book import Book
from models.user import User
from schemas.project import ProjectCreate, ProjectUpdate
from services.book_service import BookService
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime, timezone

class ProjectService:
    project_model = Project  # Add this line to expose the Project model

    @staticmethod
    def create_project(db: Session, user_id: int, project_data: ProjectCreate) -> Project:
        now = datetime.now(timezone.utc)
        project = Project(
            title=project_data.title,
            description=project_data.description,
            tags=project_data.tags,
            data=project_data.data,
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Associate book if book_id is provided
        if project_data.book_id:
            success = BookService.assign_book_to_project(db, project_data.book_id, project.id, user_id)
            if not success:
                # If book association fails, we should handle this gracefully
                # For now, we'll just log it or you could raise an exception
                pass
        
        return project

    @staticmethod
    def get_project(db: Session, project_id: int, user_id: int) -> Optional[Project]:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted == False
        ).first()
        
        if project:
            # Force refresh the books relationship
            db.refresh(project)
        
        return project

    @staticmethod
    def get_user_projects(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
        return db.query(Project).filter(
            Project.user_id == user_id,
            Project.is_deleted == False
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update_project(db: Session, project_id: int, user_id: int, project_data: ProjectUpdate) -> Optional[Project]:
        project = ProjectService.get_project(db, project_id, user_id)
        if not project:
            return None
        
        update_data = project_data.dict(exclude_unset=True)
        
        # Handle book_id separately from other fields
        book_id = update_data.pop('book_id', None)
        
        # Update other project fields
        for field, value in update_data.items():
            setattr(project, field, value)
        
        # Update the updated_at timestamp
        project.updated_at = datetime.now(timezone.utc)
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Handle book association if book_id is provided
        if book_id is not None:
            # First, remove any existing book associations
            current_books = list(project.books)
            for book in current_books:
                BookService.remove_book_from_project(db, book.id, project.id, user_id)
            
            # Then assign the new book if provided
            if book_id:
                success = BookService.assign_book_to_project(db, book_id, project.id, user_id)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Book not found or access denied"
                    )
        
        return project

    @staticmethod
    def delete_project(db: Session, project_id: int, user_id: int) -> bool:
        project = ProjectService.get_project(db, project_id, user_id)
        if not project:
            return False
        
        # Soft delete - mark as deleted instead of removing from database
        project.is_deleted = True
        project.updated_at = datetime.now(timezone.utc)
        db.add(project)
        db.commit()
        return True

    @staticmethod
    def get_all_user_projects(db: Session, user_id: int, include_deleted: bool = False, skip: int = 0, limit: int = 100) -> List[Project]:
        """Get all projects for a user, optionally including deleted ones"""
        query = db.query(Project).filter(Project.user_id == user_id)
        
        if not include_deleted:
            query = query.filter(Project.is_deleted == False)
        
        return query.offset(skip).limit(limit).all() 