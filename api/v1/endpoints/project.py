from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.project import ProjectCreate, ProjectUpdate, ProjectRead
from services.project_service import ProjectService
from models.user import User
from typing import List
from db.session import get_db
from core.dependencies import get_current_user

router = APIRouter(prefix="/project", tags=["Projects"])

@router.post("/", response_model=ProjectRead, summary="Create a new project")
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService.create_project(db, current_user.id, project_data)
    return project

@router.get("/", response_model=List[ProjectRead], summary="Get all projects for the current user")
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
    return projects

@router.get("/{project_id}", response_model=ProjectRead, summary="Get a specific project")
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
    return project

@router.put("/{project_id}", response_model=ProjectRead, summary="Update a project")
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
    return project