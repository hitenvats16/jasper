from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from schemas.book import (
    BookCreate,
    BookUpdate,
    BookRead,
    BookProjectAssociation,
    ProcessedBookData,
    BookListResponse,
    BookFilters,
    BookSortField,
    SortOrder,
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
            file.file, file.filename, custom_key=s3_key
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to S3: {str(e)}",
        )
    # Create book in database
    book = BookService.create_book(db, current_user.id, book_data, s3_key)
    
    # Create processing job asynchronously to avoid session issues
    try:
        create_book_processing_job(book.id)
    except Exception as e:
        # Log the error but don't fail the book creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create processing job for book {book.id}: {str(e)}")
    
    return book


@router.get(
    "/",
    response_model=BookListResponse,
    summary="Get all books for the current user with filtering and sorting"
)
def get_books(
    search: Optional[str] = None,
    min_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    has_processing_job: Optional[bool] = None,
    processing_status: Optional[str] = None,
    project_id: Optional[int] = None,
    sort_by: BookSortField = BookSortField.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all books for the current user with filtering, sorting, and pagination.
    
    Parameters:
    - **search**: Optional search term for title or author
    - **min_tokens**: Optional minimum number of tokens
    - **max_tokens**: Optional maximum number of tokens
    - **has_processing_job**: Optional filter for books with processing jobs
    - **processing_status**: Optional filter by processing job status (QUEUED, PROCESSING, COMPLETED, FAILED)
    - **project_id**: Optional filter by project ID
    - **sort_by**: Field to sort by (title, author, created_at, updated_at, estimated_tokens)
    - **sort_order**: Sort order (asc, desc)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    
    Returns:
    - **items**: List of books
    - **total**: Total number of books matching filters
    - **page**: Current page number
    - **page_size**: Number of items per page
    - **total_pages**: Total number of pages
    """
    filters = BookFilters(
        search=search,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        has_processing_job=has_processing_job,
        processing_status=processing_status,
        project_id=project_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return BookService.get_user_books(db, current_user.id, filters)


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
