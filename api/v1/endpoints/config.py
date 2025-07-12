from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db.session import get_db
from core.dependencies import get_current_user
from models.config import Config
from models.user import User
from schemas.config import ConfigUpdate, ConfigResponse, ConfigCreate, AdaptiveSilenceData, FixedSilenceData

router = APIRouter()

@router.get("/", response_model=ConfigResponse)
def get_user_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current user's config."""
    config = db.query(Config).filter(Config.user_id == current_user.id, Config.is_deleted == False).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    return config

@router.put("/", response_model=ConfigResponse)
def update_config(
    config_in: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's config."""
    config = db.query(Config).filter(Config.user_id == current_user.id, Config.is_deleted == False).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    
    # Convert silence_data to dict if it's a Pydantic model
    update_data = config_in.dict(exclude_unset=True)
    if 'silence_data' in update_data and update_data['silence_data'] is not None:
        if isinstance(update_data['silence_data'], (AdaptiveSilenceData, FixedSilenceData)):
            update_data['silence_data'] = update_data['silence_data'].dict()
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return config