from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from db.session import get_db
from core.dependencies import get_current_user
from models.user import User
from services.voice_generation_service import VoiceGenerationService
from schemas.voice_generation import (
    VoiceGenerationRequest, 
    VoiceGenerationResponse
)
from datetime import datetime
from models.voice_job import JobStatus
from models.processed_voice_chunks import ProcessedVoiceChunks
from models.book_voice_processing_job import BookVoiceProcessingJob

router = APIRouter()

@router.post("/generate", response_model=VoiceGenerationResponse)
async def start_voice_generation(
    request: VoiceGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start voice generation for the provided chapters.
    
    This endpoint creates a new voice generation job and sends it to the audio generation worker.
    """
    try:
        job = VoiceGenerationService.create_voice_generation_job(
            db=db,
            user_id=current_user.id,
            request=request
        )
        
        return VoiceGenerationResponse(
            job_id=job.id,
            status=job.status.value,
            message="Voice generation job created successfully",
            created_at=job.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create voice generation job: {str(e)}"
        )

@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a specific voice generation job.
    """
    job = VoiceGenerationService.get_job_status(db, job_id, current_user.id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied"
        )
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "data": job.data,
        "result": job.result,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

@router.get("/jobs", response_model=List[dict])
async def get_user_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all voice generation jobs for the current user.
    """
    jobs = VoiceGenerationService.get_user_jobs(db, current_user.id, skip, limit)
    
    return [
        {
            "job_id": job.id,
            "status": job.status.value,
            "book_id": job.book_id,
            "data": job.data,
            "result": job.result,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        for job in jobs
    ]