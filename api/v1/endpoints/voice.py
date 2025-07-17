from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session
from schemas.voice_job import VoiceProcessingJobRead
from schemas.voice import (
    VoiceUpdate,
    VoiceRead,
    VoiceListResponse,
    VoiceFilters,
    VoiceSortField,
    SortOrder,
)
from models.voice_job import VoiceProcessingJob, JobStatus
from models.voice import Voice
from utils.s3 import upload_file_to_s3, delete_file_from_s3
from services.voice_service import VoiceService
import json
from models.user import User
from typing import Optional, List
from sqlalchemy import func
from core.config import settings
from utils.message_publisher import publish_voice_job, message_publisher
from core.dependencies import get_db, get_current_user
import uuid
import logging

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
    "/jobs",
    response_model=List[VoiceProcessingJobRead],
    status_code=status.HTTP_200_OK,
    summary="List user's jobs",
    description="""
    Retrieve a list of the user's voice processing jobs.
    
    - Supports pagination with skip and limit parameters
    - Returns jobs ordered by creation date (newest first)
    - Includes job status and results
    
    **Note:** Results are ordered by creation date (newest first)
    """,
    responses={
        200: {"description": "Successfully retrieved job list"},
        401: {"description": "Unauthorized - Invalid or expired token"}
    },
    tags=["Voice Management"]
)
def list_voice_jobs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    voice_id: Optional[int] = Query(None, description="Filter jobs by voice ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all voice processing jobs for the authenticated user with pagination.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        voice_id: Optional voice ID to filter jobs
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List[VoiceProcessingJobRead]: List of voice processing jobs
    """
    query = db.query(VoiceProcessingJob).filter(VoiceProcessingJob.user_id == current_user.id, VoiceProcessingJob.is_deleted == False)
    
    if voice_id:
        # Verify voice ownership
        voice = db.query(Voice).filter_by(id=voice_id, user_id=current_user.id, is_deleted=False).first()
        if not voice:
            raise HTTPException(status_code=404, detail="Voice not found")
        query = query.filter(VoiceProcessingJob.voice_id == voice_id)
    
    jobs = query.order_by(VoiceProcessingJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs

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
    - Filter by processing job status
    - Filter voices with/without processing jobs
    
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
    },
    tags=["Voice Management"]
)
def list_voices(
    search: Optional[str] = Query(None, description="Search term for name or description"),
    is_default: Optional[bool] = Query(None, description="Filter default/custom voices"),
    has_processing_job: Optional[bool] = Query(None, description="Filter voices with processing jobs"),
    processing_status: Optional[str] = Query(None, description="Filter by processing job status"),
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
        has_processing_job: Optional filter for voices with processing jobs
        processing_status: Optional filter by processing job status
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
        has_processing_job=has_processing_job,
        processing_status=processing_status,
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
    },
    tags=["Voice Management"]
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

    # Upload file to S3
    s3_key = upload_file_to_s3(file.file, file.filename)

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

    import time
    time.sleep(0.3)
    # Create processing job using VoiceService
    job = VoiceService.create_voice_processing_job(
        db=db,
        s3_key=s3_key,
        user_id=current_user.id,
        voice_id=voice.id,
        metadata={
            "filename": file.filename,
            "name": name,
            "description": description,
            "metadata": meta_dict
        }
    )
    
    db.commit()
    logger.info(f"Created voice processing job {job.id} for voice {voice.id}")
    
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
    },
    tags=["Voice Management"]
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
        VoiceRead: Voice details
        
    Raises:
        HTTPException: If voice is not found or not owned by user
    """
    voice = VoiceService.get_voice_by_id(db, voice_id, current_user.id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
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
    },
    tags=["Voice Management"]
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
        voice_update: Updated voice information
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceRead: Updated voice information
        
    Raises:
        HTTPException: If voice is not found or not owned by user
    """
    voice = VoiceService.get_voice_by_id(db, voice_id, current_user.id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    for field, value in voice_update.dict(exclude_unset=True).items():
        setattr(voice, field, value)
    
    db.commit()
    db.refresh(voice)
    return voice