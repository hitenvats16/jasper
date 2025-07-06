from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Query
from sqlalchemy.orm import Session
from schemas.default_voice import DefaultVoiceCreate, DefaultVoiceUpdate, DefaultVoiceRead
from models.default_voice import DefaultVoice
from models.user import User
from utils.s3 import upload_file_to_s3
from core.dependencies import get_db, get_current_user
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource not found"},
        422: {"description": "Validation Error - Invalid request data"}
    }
)

def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to ensure the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get(
    "/default-voices",
    response_model=List[DefaultVoiceRead],
    status_code=status.HTTP_200_OK,
    summary="List all default voices",
    description="""
    Retrieve a list of all default voices (admin only).
    
    - Returns all default voices in the system
    - Includes public and private voices
    - Admin access required
    """,
    responses={
        200: {"description": "Successfully retrieved default voices list"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Admin access required"}
    }
)
def list_default_voices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List all default voices (admin only).
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated admin user
    
    Returns:
        List[DefaultVoiceRead]: List of default voices
    """
    voices = db.query(DefaultVoice).offset(skip).limit(limit).all()
    return voices

@router.post(
    "/default-voices",
    response_model=DefaultVoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new default voice",
    description="""
    Create a new default voice (admin only).
    
    - Uploads audio file to S3
    - Creates default voice record
    - Admin access required
    
    **Note:** 
    - File must be a valid audio format
    - Name is required
    - Description and public status are optional
    """,
    responses={
        201: {"description": "Default voice successfully created"},
        400: {"description": "Invalid file format"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Admin access required"}
    }
)
async def create_default_voice(
    name: str = Form(..., description="Name of the default voice"),
    description: Optional[str] = Form(None, description="Optional description of the voice"),
    is_public: bool = Form(True, description="Whether the voice should be public"),
    file: UploadFile = File(..., description="Audio file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new default voice (admin only).
    
    Args:
        name: Name of the default voice
        description: Optional description
        is_public: Whether the voice should be public
        file: Audio file to upload
        db: Database session
        current_user: Current authenticated admin user
    
    Returns:
        DefaultVoiceRead: Created default voice information
        
    Raises:
        HTTPException: If file format is invalid
    """
    # Upload file to S3
    s3_key = upload_file_to_s3(file.file, file.filename, file.content_type)

    # Create default voice record
    default_voice = DefaultVoice(
        name=name,
        description=description,
        s3_key=s3_key,
        is_public=is_public
    )
    db.add(default_voice)
    db.commit()
    db.refresh(default_voice)

    logger.info(f"Admin {current_user.id} created default voice {default_voice.id}")
    return default_voice

@router.get(
    "/default-voices/{voice_id}",
    response_model=DefaultVoiceRead,
    status_code=status.HTTP_200_OK,
    summary="Get default voice details",
    description="""
    Retrieve detailed information about a specific default voice (admin only).
    
    - Returns complete default voice information
    - Admin access required
    
    **Note:** Only accessible by administrators
    """,
    responses={
        200: {"description": "Successfully retrieved default voice details"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Admin access required"},
        404: {"description": "Default voice not found"}
    }
)
def get_default_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get a specific default voice by ID (admin only).
    
    Args:
        voice_id: ID of the default voice to retrieve
        db: Database session
        current_user: Current authenticated admin user
    
    Returns:
        DefaultVoiceRead: Default voice details
        
    Raises:
        HTTPException: If default voice is not found
    """
    default_voice = db.query(DefaultVoice).filter(DefaultVoice.id == voice_id).first()
    if not default_voice:
        raise HTTPException(status_code=404, detail="Default voice not found")
    return default_voice

@router.put(
    "/default-voices/{voice_id}",
    response_model=DefaultVoiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update default voice details",
    description="""
    Update the details of a specific default voice (admin only).
    
    - Can update name, description, and public status
    - Admin access required
    - Returns updated default voice information
    
    **Note:** Only accessible by administrators
    """,
    responses={
        200: {"description": "Successfully updated default voice details"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Admin access required"},
        404: {"description": "Default voice not found"}
    }
)
def update_default_voice(
    voice_id: int,
    voice_update: DefaultVoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a default voice's details (admin only).
    
    Args:
        voice_id: ID of the default voice to update
        voice_update: Updated default voice information
        db: Database session
        current_user: Current authenticated admin user
    
    Returns:
        DefaultVoiceRead: Updated default voice information
        
    Raises:
        HTTPException: If default voice is not found
    """
    default_voice = db.query(DefaultVoice).filter(DefaultVoice.id == voice_id).first()
    if not default_voice:
        raise HTTPException(status_code=404, detail="Default voice not found")
    
    for field, value in voice_update.dict(exclude_unset=True).items():
        setattr(default_voice, field, value)
    
    db.commit()
    db.refresh(default_voice)
    
    logger.info(f"Admin {current_user.id} updated default voice {voice_id}")
    return default_voice

@router.delete(
    "/default-voices/{voice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a default voice",
    description="""
    Delete a specific default voice (admin only).
    
    - Permanently removes the default voice
    - Admin access required
    
    **Note:** This action cannot be undone
    """,
    responses={
        204: {"description": "Default voice successfully deleted"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Admin access required"},
        404: {"description": "Default voice not found"}
    }
)
def delete_default_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a default voice (admin only).
    
    Args:
        voice_id: ID of the default voice to delete
        db: Database session
        current_user: Current authenticated admin user
        
    Raises:
        HTTPException: If default voice is not found
    """
    default_voice = db.query(DefaultVoice).filter(DefaultVoice.id == voice_id).first()
    if not default_voice:
        raise HTTPException(status_code=404, detail="Default voice not found")
    
    db.delete(default_voice)
    db.commit()
    
    logger.info(f"Admin {current_user.id} deleted default voice {voice_id}") 