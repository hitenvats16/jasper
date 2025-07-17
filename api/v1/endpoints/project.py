from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    SortOrder,
    ProjectSortField
)
from services.project_service import ProjectService
from models.user import User
from typing import List, Optional
from db.session import get_db
from core.dependencies import get_current_user
from sqlalchemy import or_, and_, desc, asc, func

router = APIRouter(prefix="/project", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, summary="Create a new project")
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.create_project(db, current_user.id, project_data)
    return ProjectResponse.from_project(project)

@router.get("/", response_model=ProjectListResponse, summary="Get all projects for the current user")
def get_projects(
    search: Optional[str] = Query(None, description="Search in project title and description"),
    tag: Optional[str] = Query(None, description="Filter by specific tag"),
    has_books: Optional[bool] = Query(None, description="Filter projects that have or don't have books"),
    min_books: Optional[int] = Query(None, ge=0, description="Filter projects with at least this many books"),
    max_books: Optional[int] = Query(None, ge=0, description="Filter projects with at most this many books"),
    sort_by: ProjectSortField = Query(ProjectSortField.created_at, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    include_deleted: bool = Query(False, description="Include deleted projects"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all projects for the current user with filtering, sorting, and pagination.
    
    Filters:
    - Search by title/description
    - Filter by tag
    - Filter by book count
    - Filter by has_books status
    
    Sorting:
    - Sort by created_at, updated_at, title, or book count
    - Ascending or descending order
    
    Pagination:
    - Page number and page size
    """
    # Start with base query
    query = db.query(ProjectService.project_model)
    
    # Apply user filter
    query = query.filter(ProjectService.project_model.user_id == current_user.id)
    
    # Handle deleted status
    if not include_deleted:
        query = query.filter(ProjectService.project_model.is_deleted == False)
    
    # Apply search if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ProjectService.project_model.title.ilike(search_term),
                ProjectService.project_model.description.ilike(search_term)
            )
        )
    
    # Apply tag filter if provided
    if tag:
        # Note: This assumes tags are stored as a JSON array
        query = query.filter(ProjectService.project_model.tags.contains([tag]))
    
    # Apply book count filters
    if has_books is not None:
        if has_books:
            query = query.filter(ProjectService.project_model.books.any())
        else:
            query = query.filter(~ProjectService.project_model.books.any())
    
    if min_books is not None:
        query = query.having(func.count(ProjectService.project_model.books) >= min_books)
        
    if max_books is not None:
        query = query.having(func.count(ProjectService.project_model.books) <= max_books)
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply sorting
    if sort_by == ProjectSortField.book_count:
        # Special handling for book count sorting
        query = query.outerjoin(ProjectService.project_model.books)\
                    .group_by(ProjectService.project_model.id)\
                    .order_by(
                        desc(func.count(ProjectService.project_model.books.any()))
                        if sort_order == SortOrder.desc
                        else asc(func.count(ProjectService.project_model.books.any()))
                    )
    else:
        # Regular field sorting
        sort_column = getattr(ProjectService.project_model, sort_by.value)
        query = query.order_by(desc(sort_column) if sort_order == SortOrder.desc else asc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    projects = query.all()
    
    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size
    
    # Prepare response
    return ProjectListResponse(
        items=[ProjectResponse.from_project(project) for project in projects],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{project_id}", response_model=ProjectResponse, summary="Get a specific project")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return ProjectResponse.from_project(project)

@router.put("/{project_id}", response_model=ProjectResponse, summary="Update a project")
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.update_project(db, project_id, current_user.id, project_data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return ProjectResponse.from_project(project)