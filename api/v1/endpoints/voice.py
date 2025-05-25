from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Request, Security, Query
from sqlalchemy.orm import Session
from db.session import SessionLocal
from schemas.voice_job import VoiceProcessingJobCreate, VoiceProcessingJobRead
from schemas.voice import VoiceCreate, VoiceUpdate, VoiceRead, VoiceList
from models.voice_job import VoiceProcessingJob, JobStatus
from models.voice import Voice
from utils.s3 import upload_file_to_s3, delete_file_from_s3
import json
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import decode_access_token
from models.user import User
from typing import Optional
from sqlalchemy import func
from core.config import settings
from utils.message_publisher import publish_voice_job

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

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises 401 if token is invalid or expired, 404 if user not found.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter_by(id=payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post(
    "/process",
    response_model=VoiceProcessingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process voice sample",
    description="""
    Upload and process a voice sample for analysis.
    
    - Accepts audio file upload
    - Stores file in S3
    - Creates processing job
    - Enqueues job for asynchronous processing
    
    **Note:** 
    - File must be a valid audio format
    - Processing is asynchronous
    - Job status can be checked using the job ID
    """,
    responses={
        202: {"description": "Job successfully created and queued"},
        400: {"description": "Invalid file format or metadata"},
        401: {"description": "Unauthorized - Invalid or expired token"}
    },
    tags=["Voice Management"]
)
async def enqueue_voice_job(
    file: UploadFile = File(...),
    metadata: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and process a voice sample.
    
    Args:
        file: Audio file to process
        metadata: Optional JSON string containing additional metadata
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        VoiceProcessingJobRead: Created job information
        
    Raises:
        HTTPException: If file format is invalid or metadata is malformed
    """
    try:
        meta_dict = json.loads(metadata) if metadata else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    s3_url = upload_file_to_s3(file.file, file.filename, file.content_type)
    job = VoiceProcessingJob(s3_link=s3_url, metadata=meta_dict, status=JobStatus.QUEUED)
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Publish job to RabbitMQ queue
    publish_voice_job(job.id)
    return job

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
def get_voice_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get the status and results of a voice processing job.
    
    Args:
        job_id: ID of the job to retrieve
        db: Database session
    
    Returns:
        VoiceProcessingJobRead: Job status and results
        
    Raises:
        HTTPException: If job is not found
    """
    job = db.query(VoiceProcessingJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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
    
    s3_url = upload_file_to_s3(file.file, file.filename, file.content_type)
    voice = Voice(
        name=name,
        description=description,
        s3_link=s3_url,
        voice_metadata=meta_dict,
        user_id=current_user.id
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
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
    
    update_data = voice_update.dict(exclude_unset=True)
    for field, value in update_data.items():
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
    voice = db.query(Voice).filter(Voice.id == voice_id, Voice.user_id == current_user.id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Delete from S3
    try:
        delete_file_from_s3(voice.s3_link)
    except Exception as e:
        # Log the error but continue with database deletion
        print(f"Error deleting file from S3: {str(e)}")
    
    # Delete from database
    db.delete(voice)
    db.commit()
    return None 