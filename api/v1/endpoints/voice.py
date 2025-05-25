from fastapi import APIRouter, status, Depends, File, UploadFile, Form, HTTPException, Request, Security, Query
from sqlalchemy.orm import Session
from db.session import SessionLocal
from schemas.voice_job import VoiceProcessingJobCreate, VoiceProcessingJobRead
from schemas.voice import VoiceCreate, VoiceUpdate, VoiceRead, VoiceList
from models.voice_job import VoiceProcessingJob, JobStatus
from models.voice import Voice
from workers.rabbitmq import RabbitMQManager
from utils.s3 import upload_file_to_s3, delete_file_from_s3
import json
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import decode_access_token
from models.user import User
from typing import Optional
from sqlalchemy import func
from core.config import settings



router = APIRouter()

# RabbitMQ manager instance
rabbitmq_manager = RabbitMQManager()

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials = Security(security)):
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
    summary="Upload and process a voice sample",
    description="Upload an audio file, store it in S3, create a processing job, and enqueue it. Requires authentication.",
    tags=["voice"],
)
async def enqueue_voice_job(
    file: UploadFile = File(...),
    metadata: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    rabbitmq_manager.publish_message(
        settings.VOICE_PROCESSING_QUEUE,
        {"job_id": job.id}
    )
    return job

@router.get(
    "/jobs/{job_id}",
    response_model=VoiceProcessingJobRead,
    status_code=status.HTTP_200_OK,
    summary="Get voice processing job status/result",
    description="Get the status and result of a voice processing job by job ID.",
    tags=["voice"],
)
def get_voice_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(VoiceProcessingJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get(
    "/list",
    response_model=VoiceList,
    status_code=status.HTTP_200_OK,
    summary="List user's voices",
    description="Get a paginated list of the authenticated user's voices.",
    tags=["voice"],
)
def list_voices(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all voices for the authenticated user with pagination"""
    total = db.query(func.count(Voice.id)).filter(Voice.user_id == current_user.id).scalar()
    voices = db.query(Voice).filter(Voice.user_id == current_user.id).offset(skip).limit(limit).all()
    return {"items": voices, "total": total}

@router.post(
    "/create",
    response_model=VoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new voice",
    description="Upload a voice file and create a new voice record.",
    tags=["voice"],
)
async def create_voice(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new voice record with an uploaded file"""
    try:
        meta_dict = json.loads(metadata) if metadata else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    s3_url = upload_file_to_s3(file.file, file.filename, file.content_type)
    voice = Voice(
        name=name,
        description=description,
        s3_link=s3_url,
        metadata=meta_dict,
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
    description="Get details of a specific voice by ID.",
    tags=["voice"],
)
def get_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific voice by ID"""
    voice = db.query(Voice).filter(Voice.id == voice_id, Voice.user_id == current_user.id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    return voice

@router.put(
    "/{voice_id}",
    response_model=VoiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update voice details",
    description="Update the details of a specific voice.",
    tags=["voice"],
)
def update_voice(
    voice_id: int,
    voice_update: VoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a voice's details"""
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
    summary="Delete a voice",
    description="Delete a voice and its associated file from S3.",
    tags=["voice"],
)
def delete_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a voice and its associated file"""
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