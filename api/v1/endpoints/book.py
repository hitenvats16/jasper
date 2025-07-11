from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from schemas.book import (
    BookCreate,
    BookUpdate,
    BookRead,
    BookProjectAssociation,
    ProcessedBookData,
)
from services.book_service import BookService
from models.user import User
from typing import List, Optional
from db.session import get_db
from core.dependencies import get_current_user
from utils.s3 import upload_file_to_s3
import json
from utils.message_publisher import create_book_processing_job

router = APIRouter(prefix="/book", tags=["Books"])


@router.post("/", response_model=BookRead, summary="Create a new book with file upload")
async def create_book(
    file: UploadFile = File(..., description="Book file (max 20MB)"),
    title: str = Form(..., description="Book title"),
    author: str = Form(..., description="Book author"),
    data: Optional[str] = Form(None, description="JSON data as string"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new book entry with file upload.
    - **file**: Book file (PDF) - max 20MB
    - **title**: Book title
    - **author**: Book author
    - **data**: Optional JSON data as string
    """
    # Validate file size (20MB limit)
    if not BookService.validate_file_size(file.size):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 20MB limit",
        )
    # Validate file type
    if not BookService.validate_file_type(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PDF",
        )
    # Parse JSON data if provided
    json_data = None
    if data:
        try:
            json_data = json.loads(data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON data format",
            )
    # Create book data object
    book_data = BookCreate(title=title, author=author, data=json_data)
    # Generate S3 key
    s3_key = BookService.generate_s3_key(current_user.id, file.filename)
    # Upload file to S3
    try:
        upload_file_to_s3(
            file.file, file.filename, file.content_type, custom_key=s3_key
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to S3: {str(e)}",
        )
    # Create book in database
    book = BookService.create_book(db, current_user.id, book_data, s3_key)
    create_book_processing_job(book)
    return book


@router.get(
    "/", response_model=List[BookRead], summary="Get all books for the current user"
)
def get_books(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all books for the current user"""
    books = BookService.get_user_books(db, current_user.id, skip=skip, limit=limit)
    return books


@router.get("/{book_id}", response_model=BookRead, summary="Get a specific book")
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific book by ID"""
    book = BookService.get_book(db, book_id, current_user.id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


@router.get(
    "/{book_id}/processed",
    response_model=ProcessedBookData,
    summary="Get processed book data",
)
def get_processed_book_data(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get processed book data including parsed structure and processing status.

    Returns:
    - **book_id**: The book ID
    - **title**: Book title
    - **author**: Book author
    - **processing_status**: Current processing status (not_processed, queued, processing, completed, failed)
    - **processed_data**: The parsed book structure (chapters, sections, etc.)
    - **processing_result**: Result information from the latest processing job
    - **last_processing_job**: Details about the most recent processing job
    """
    processed_data = BookService.get_processed_book_data(db, book_id, current_user.id)
    if not processed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return processed_data


@router.put("/{book_id}", response_model=BookRead, summary="Update a book")
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a book's title, author, and data fields.
    - **title**: New book title (optional)
    - **author**: New book author (optional)
    - **data**: New JSON data (optional)
    """
    book = BookService.update_book(db, book_id, current_user.id, book_data)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


# Project association endpoints
@router.post("/{book_id}/assign-project", summary="Assign a book to a project")
def assign_book_to_project(
    book_id: int,
    association: BookProjectAssociation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign a book to a project"""

    success = BookService.assign_book_to_project(
        db, book_id, association.project_id, current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book or project not found"
        )
    return {"message": "Book assigned to project successfully"}


@router.post(
    "/{book_id}/remove-project/{project_id}", summary="Remove a book from a project"
)
def remove_book_from_project(
    book_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a book from a project"""
    success = BookService.remove_book_from_project(
        db, book_id, project_id, current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book or project not found"
        )

    # Force refresh the project to ensure the relationship is updated
    from services.project_service import ProjectService

    project = ProjectService.get_project(db, project_id, current_user.id)

    return {
        "message": "Book removed from project successfully",
        "project_book_count": len(project.books) if project else 0,
    }


@router.get(
    "/debug/project/{project_id}/books", summary="Debug: Get all books for a project"
)
def debug_project_books(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debug endpoint to check the current books associated with a project"""
    from services.project_service import ProjectService

    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return {
        "project_id": project.id,
        "project_title": project.title,
        "book_count": len(project.books),
        "book_ids": [book.id for book in project.books],
        "book_titles": [book.title for book in project.books],
    }
