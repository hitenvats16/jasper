from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session
from db.session import SessionLocal
from schemas.voice_job import VoiceProcessingJobCreate, VoiceProcessingJobRead
from schemas.voice import VoiceCreate, VoiceUpdate, VoiceRead, VoiceList
from models.voice_job import VoiceProcessingJob, JobStatus
from models.voice import Voice
from utils.s3 import upload_file_to_s3, delete_file_from_s3
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
    "/jobs/{job_id}",
    response_model=VoiceProcessingJobRead,
    status_code=status.HTTP_200_OK,
    summary="Get job status",
    description="""
    Retrieve the status and results of a voice processing job.
    
    - Returns current job status
    - Includes processing results if completed
    - Shows error message if failed
    
    **Note:** Job status can be: QUEUED, PROCESSING, COMPLETED, or FAILED
    """,
    responses={
        200: {"description": "Successfully retrieved job status"},
        404: {"description": "Job not found"}
    },
    tags=["Voice Management"]
)
def get_voice_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status and results of a voice processing job.
    
    Args:
        job_id: ID of the job to retrieve
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceProcessingJobRead: Job status and results
        
    Raises:
        HTTPException: If job is not found or user doesn't have access
    """
    job = db.query(VoiceProcessingJob).filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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
    query = db.query(VoiceProcessingJob).filter(VoiceProcessingJob.user_id == current_user.id)
    
    if voice_id:
        # Verify voice ownership
        voice = db.query(Voice).filter_by(id=voice_id, user_id=current_user.id).first()
        if not voice:
            raise HTTPException(status_code=404, detail="Voice not found")
        query = query.filter(VoiceProcessingJob.voice_id == voice_id)
    
    jobs = query.order_by(VoiceProcessingJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs

@router.get(
    "/list",
    response_model=VoiceList,
    status_code=status.HTTP_200_OK,
    summary="List user's voices",
    description="""
    Retrieve a paginated list of the user's voice samples.
    
    - Supports pagination with skip and limit parameters
    - Returns total count of available voices
    - Includes basic voice information
    
    **Note:** Results are ordered by creation date (newest first)
    """,
    responses={
        200: {"description": "Successfully retrieved voice list"},
        401: {"description": "Unauthorized - Invalid or expired token"}
    },
    tags=["Voice Management"]
)
def list_voices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all voices for the authenticated user with pagination.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceList: Paginated list of voices with total count
    """
    total = db.query(func.count(Voice.id)).filter(Voice.user_id == current_user.id).scalar()
    voices = db.query(Voice).filter(Voice.user_id == current_user.id).offset(skip).limit(limit).all()
    return {"items": voices, "total": total}

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
    s3_link = upload_file_to_s3(file.file, file.filename, file.content_type)

    # Create voice record
    voice = Voice(
        name=name,
        description=description,
        voice_metadata=meta_dict,
        s3_link=s3_link,
        user_id=current_user.id
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)

    print("created voice",voice)

    # Create processing job
    job = VoiceProcessingJob(
        s3_link=s3_link,
        status=JobStatus.QUEUED,
        user_id=current_user.id,
        voice_id=voice.id,
        meta_data={
            "filename": file.filename,
            "name": name,
            "description": description,
            "metadata": meta_dict
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    print("created job",job)
    
    # Publish message to queue
    message = {
        "job_id": job.id,
        "s3_link": s3_link,
        "user_id": current_user.id,
        "voice_id": voice.id,
        "metadata": {
            "filename": file.filename,
            "name": name,
            "description": description,
            "metadata": meta_dict
        }
    }
    message_publisher.publish(settings.VOICE_PROCESSING_QUEUE, message)
    
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
    voice = db.query(Voice).filter(Voice.id == voice_id, Voice.user_id == current_user.id).first()
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
    voice = db.query(Voice).filter(Voice.id == voice_id, Voice.user_id == current_user.id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    for field, value in voice_update.dict(exclude_unset=True).items():
        setattr(voice, field, value)
    
    db.commit()
    db.refresh(voice)
    return voice

@router.delete(
    "/{voice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete voice",
    description="""
    Delete a voice and its associated file.
    
    - Removes voice record from database
    - Deletes associated file from S3
    - Verifies user ownership
    
    **Note:** 
    - Operation is irreversible
    - Only accessible by the voice owner
    - S3 deletion errors are logged but don't prevent database deletion
    """,
    responses={
        204: {"description": "Voice successfully deleted"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        404: {"description": "Voice not found"}
    },
    tags=["Voice Management"]
)
def delete_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a voice and its associated file.
    
    Args:
        voice_id: ID of the voice to delete
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        None
        
    Raises:
        HTTPException: If voice is not found or not owned by user
    """
    voice = db.query(Voice).filter_by(id=voice_id, user_id=current_user.id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Delete from S3
    try:
        delete_file_from_s3(voice.s3_link)
    except Exception as e:
        logger.error(f"Error deleting file from S3: {str(e)}")
    
    # Delete from database
    db.delete(voice)
    db.commit()
    return None 