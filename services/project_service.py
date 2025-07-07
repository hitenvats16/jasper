from sqlalchemy.orm import Session
from models.project import Project
from models.user import User
from schemas.project import ProjectCreate, ProjectUpdate
from typing import List, Optional

class ProjectService:
    @staticmethod
    def create_project(db: Session, user_id: int, project_data: ProjectCreate) -> Project:
        project = Project(
            title=project_data.title,
            description=project_data.description,
            tags=project_data.tags,
            data=project_data.data,
            user_id=user_id
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_project(db: Session, project_id: int, user_id: int) -> Optional[Project]:
        return db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted == False
        ).first()

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
        for field, value in update_data.items():
            setattr(project, field, value)
        
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project_id: int, user_id: int) -> bool:
        project = ProjectService.get_project(db, project_id, user_id)
        if not project:
            return False
        
        # Soft delete - mark as deleted instead of removing from database
        project.is_deleted = True
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