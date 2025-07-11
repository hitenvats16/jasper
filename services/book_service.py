from sqlalchemy.orm import Session
from models.book import Book
from models.project import Project
from models.user import User
from models.book_processing_job import BookProcessingJob
from models.voice_job import JobStatus
from schemas.book import BookCreate, BookUpdate
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
import uuid
import os

class BookService:
    @staticmethod
    def create_book(db: Session, user_id: int, book_data: BookCreate, s3_key: Optional[str] = None) -> Book:
        book = Book(
            title=book_data.title,
            author=book_data.author,
            s3_key=s3_key,
            user_id=user_id,
            data=book_data.data
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book

    @staticmethod
    def get_book(db: Session, book_id: int, user_id: int) -> Optional[Book]:
        return db.query(Book).filter(
            Book.id == book_id,
            Book.user_id == user_id,
            Book.is_deleted == False
        ).first()

    @staticmethod
    def get_user_books(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Book]:
        return db.query(Book).filter(
            Book.user_id == user_id,
            Book.is_deleted == False
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_processed_book_data(db: Session, book_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get processed book data including parsing results and job status"""
        # Get the book
        book = BookService.get_book(db, book_id, user_id)
        if not book:
            return None

        # Get the latest processing job for this book
        latest_job = db.query(BookProcessingJob).filter(
            BookProcessingJob.book_id == book_id,
            BookProcessingJob.user_id == user_id,
            BookProcessingJob.is_deleted == False
        ).order_by(BookProcessingJob.created_at.desc()).first()
        
        # Determine processing status
        processing_status = "not_processed"
        if latest_job:
            if latest_job.status == JobStatus.COMPLETED:
                processing_status = "completed"
            elif latest_job.status == JobStatus.PROCESSING:
                processing_status = "processing"
            elif latest_job.status == JobStatus.QUEUED:
                processing_status = "queued"
            elif latest_job.status == JobStatus.FAILED:
                processing_status = "failed"
    
        # Prepare response data
        response_data = {
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "processing_status": processing_status,
            "processed_data": latest_job.processed_data if latest_job else None,
            "processing_result": latest_job.result if latest_job else None,
            "last_processing_job": {
                "id": latest_job.id,
                "status": latest_job.status.value if latest_job else None,
                "created_at": latest_job.created_at.isoformat() if latest_job else None,
                "updated_at": latest_job.updated_at.isoformat() if latest_job else None,
                "data": latest_job.data if latest_job else None
            } if latest_job else None,
            "created_at": book.created_at,
            "updated_at": book.updated_at
        }
        
        return response_data

    @staticmethod
    def update_book(db: Session, book_id: int, user_id: int, book_data: BookUpdate) -> Optional[Book]:
        book = BookService.get_book(db, book_id, user_id)
        if not book:
            return None
        
        update_data = book_data.dict(exclude_unset=True)
        
        # Check if trying to mark as deleted
        if 'is_deleted' in update_data and update_data['is_deleted'] is True:
            # Check if book belongs to any projects
            if book.projects and len(book.projects) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete book that belongs to one or more projects. Remove book from all projects first."
                )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(book, field, value)
        
        db.add(book)
        db.commit()
        db.refresh(book)
        return book

    @staticmethod
    def generate_s3_key(user_id: int, filename: str) -> str:
        """Generate S3 key for book file"""
        clean_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.')).rstrip()
        unique_id = str(uuid.uuid4())
        s3_key = f"books/{user_id}_{unique_id}_{clean_filename}"
        return s3_key

    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: int = 20) -> bool:
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes

    @staticmethod
    def validate_file_type(filename: str) -> bool:
        allowed_extensions = {'.pdf'}
        file_extension = os.path.splitext(filename.lower())[1]
        return file_extension in allowed_extensions

    # Project association methods
    @staticmethod
    def assign_book_to_project(db: Session, book_id: int, project_id: int, user_id: int) -> bool:
        """Assign a book to a project"""
        # Check if book exists and belongs to user
        book = BookService.get_book(db, book_id, user_id)
        if not book:
            return False
        
        # Check if project exists and belongs to user
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted == False
        ).first()
        
        if not project:
            return False
        
        # Add project to book's projects
        if project not in book.projects:
            book.projects.append(project)
            db.add(book)
            db.commit()
        
        return True

    @staticmethod
    def remove_book_from_project(db: Session, book_id: int, project_id: int, user_id: int) -> bool:
        """Remove a book from a project"""
        # Check if book exists and belongs to user
        book = BookService.get_book(db, book_id, user_id)
        if not book:
            return False
        
        # Check if project exists and belongs to user
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted == False
        ).first()
        
        if not project:
            return False
        
        # Check if the association exists
        if project not in book.projects:
            return True  # Already not associated
        
        # Remove project from book's projects
        book.projects.remove(project)
        db.add(book)
        db.commit()
        
        # Refresh both objects to ensure the relationship is updated
        db.refresh(book)
        db.refresh(project)
        
        return True