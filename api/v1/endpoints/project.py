from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.project import ProjectCreate, ProjectUpdate, ProjectRead
from services.project_service import ProjectService
from models.user import User
from typing import List, Optional
from db.session import get_db
from core.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/project", tags=["Projects"])

# Custom response model to handle book IDs
class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str = None
    tags: List[str] = None
    data: Optional[dict] = None
    user_id: int
    book_ids: List[int] = []
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
    
    @classmethod
    def from_project(cls, project):
        return cls(
            id=project.id,
            title=project.title,
            description=project.description,
            tags=project.tags,
            data=project.data or None,
            user_id=project.user_id,
            book_ids=[book.id for book in project.books],
            created_at=project.created_at.isoformat() if project.created_at else None,
            updated_at=project.updated_at.isoformat() if project.updated_at else None
        )

@router.post("/", response_model=ProjectResponse, summary="Create a new project")
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.create_project(db, current_user.id, project_data)
    return ProjectResponse.from_project(project)

@router.get("/", response_model=List[ProjectResponse], summary="Get all projects for the current user")
def get_projects(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if include_deleted:
        projects = ProjectService.get_all_user_projects(db, current_user.id, include_deleted=True, skip=skip, limit=limit)
    else:
        projects = ProjectService.get_user_projects(db, current_user.id, skip=skip, limit=limit)
    return [ProjectResponse.from_project(project) for project in projects]

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