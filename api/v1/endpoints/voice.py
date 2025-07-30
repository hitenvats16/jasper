from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session
from schemas.voice import (
    VoiceUpdate,
    VoiceRead,
    VoiceListResponse,
    VoiceFilters,
    VoiceSortField,
    SortOrder,
)
from models.voice import Voice
from utils.s3 import upload_file_to_s3, delete_file_from_s3
from services.voice_service import VoiceService
import json
from models.user import User
from typing import Optional, List
from sqlalchemy import func
from core.config import settings
from utils.message_publisher import message_publisher
from core.dependencies import get_db, get_current_user
import uuid
import logging
import io
from pydub import AudioSegment

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/voice",
    tags=["Voice Management"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource not found"},
        422: {"description": "Validation Error - Invalid request data"}
    }
)

@router.get(
    "/list",
    response_model=VoiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user's voices with filtering and sorting",
    description="""
    Retrieve a filtered, sorted, and paginated list of the user's voice samples.
    
    **Filtering Options:**
    - Search by name or description
    - Filter default/custom voices
    
    **Sorting Options:**
    - Sort by name, creation date, or last update
    - Ascending or descending order
    
    **Pagination:**
    - Page number and size control
    - Returns total count and pages
    
    **Note:** Results are ordered by creation date (newest first) by default
    """,
    responses={
        200: {"description": "Successfully retrieved voice list"},
        401: {"description": "Unauthorized - Invalid or expired token"}
    }
)
def list_voices(
    search: Optional[str] = Query(None, description="Search term for name or description"),
    is_default: Optional[bool] = Query(None, description="Filter default/custom voices"),
    sort_by: VoiceSortField = Query(VoiceSortField.CREATED_AT, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all voices for the authenticated user with filtering, sorting, and pagination.
    
    Args:
        search: Optional search term for name or description
        is_default: Optional filter for default/custom voices
        sort_by: Field to sort by (name, created_at, updated_at)
        sort_order: Sort order (asc, desc)
        page: Page number (default: 1)
        page_size: Items per page (default: 10, max: 100)
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceListResponse: Paginated list of voices with metadata
    """
    filters = VoiceFilters(
        search=search,
        is_default=is_default,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return VoiceService.get_user_voices(db, current_user.id, filters)

@router.post(
    "/create",
    response_model=VoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new voice",
    description="""
    Upload and create a new voice sample.
    
    - Accepts audio file upload
    - Stores file in S3
    - Creates voice record with metadata
    - Associates voice with current user
    
    **Note:** 
    - File must be a valid audio format
    - Name is required
    - Description and metadata are optional
    """,
    responses={
        201: {"description": "Voice successfully created"},
        400: {"description": "Invalid file format or metadata"},
        401: {"description": "Unauthorized - Invalid or expired token"}
    }
)
async def create_voice(
    name: str = Form(..., description="Name of the voice"),
    description: Optional[str] = Form(None, description="Optional description of the voice"),
    metadata: Optional[str] = Form(None, description="Optional JSON metadata"),
    file: UploadFile = File(..., description="Audio file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new voice record with an uploaded file.
    
    Args:
        name: Name of the voice
        description: Optional description
        metadata: Optional JSON metadata
        file: Audio file to upload
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceRead: Created voice information
        
    Raises:
        HTTPException: If file format is invalid or metadata is malformed
    """
    try:
        meta_dict = json.loads(metadata) if metadata else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    # Read the uploaded file into memory
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer for potential future use
    
    # Load audio using pydub
    try:
        audio = AudioSegment.from_file(io.BytesIO(file_content))
    except Exception as e:
        logger.error(f"Failed to load audio file: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid audio file format")
    
    # Trim audio to first 15 seconds (15000 milliseconds)
    max_duration_ms = 15000
    if len(audio) > max_duration_ms:
        audio = audio[:max_duration_ms]
        logger.info(f"Trimmed audio from {len(audio)}ms to {max_duration_ms}ms")
    
    # Export the trimmed audio to a buffer
    output_buffer = io.BytesIO()
    audio.export(output_buffer, format=file.filename.split('.')[-1] if '.' in file.filename else 'mp3')
    output_buffer.seek(0)
    
    # Upload trimmed file to S3
    s3_key = upload_file_to_s3(output_buffer, file.filename)

    # Create voice record
    voice = Voice(
        name=name,
        description=description,
        voice_metadata=meta_dict,
        s3_key=s3_key,
        user_id=current_user.id
    ) 
    db.add(voice)
    db.commit()
    db.refresh(voice)

    logger.info(f"Created voice {voice.id} for user {current_user.id}")
    return voice

@router.get(
    "/{voice_id}",
    response_model=VoiceRead,
    status_code=status.HTTP_200_OK,
    summary="Get voice details",
    description="""
    Retrieve detailed information about a specific voice.
    
    - Returns complete voice information
    - Includes S3 link and metadata
    - Verifies user ownership
    
    **Note:** Only accessible by the voice owner
    """,
    responses={
        200: {"description": "Successfully retrieved voice details"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        404: {"description": "Voice not found"}
    }
)
def get_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific voice by ID.
    
    Args:
        voice_id: ID of the voice to retrieve
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceRead: Voice information
        
    Raises:
        HTTPException: If voice not found or not owned by user
    """
    voice = VoiceService.get_voice_by_id(db, voice_id, current_user.id)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice not found"
        )
    return voice

@router.put(
    "/{voice_id}",
    response_model=VoiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update voice details",
    description="""
    Update the details of a specific voice.
    
    - Can update name, description, and metadata
    - Verifies user ownership
    - Returns updated voice information
    
    **Note:** Only accessible by the voice owner
    """,
    responses={
        200: {"description": "Successfully updated voice details"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        404: {"description": "Voice not found"}
    }
)
def update_voice(
    voice_id: int,
    voice_update: VoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a voice's details.
    
    Args:
        voice_id: ID of the voice to update
        voice_update: Updated voice data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceRead: Updated voice information
        
    Raises:
        HTTPException: If voice not found or not owned by user
    """
    voice = VoiceService.get_voice_by_id(db, voice_id, current_user.id)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice not found"
        )

    # Update voice fields
    for field, value in voice_update.dict(exclude_unset=True).items():
        setattr(voice, field, value)

    db.add(voice)
    db.commit()
    db.refresh(voice)
    return voice
