from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from db.session import get_db
from core.dependencies import get_current_user
from models.user import User
from services.voice_generation_service import VoiceGenerationService
from schemas.voice_generation import (
    VoiceGenerationRequest, 
    VoiceGenerationResponse,
    ProcessedVoiceChunkResponse,
    VoiceGenerationEstimateResponse
)
from datetime import datetime
from models.voice_job import JobStatus
from models.processed_voice_chunks import ProcessedVoiceChunks, ProcessedVoiceChunksType
from models.book_voice_processing_job import BookVoiceProcessingJob
from models.book import Book

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
    print(f"Starting voice generation for user {current_user.id} and book {request.book_id}")
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
    
@router.post("/estimate", response_model=VoiceGenerationEstimateResponse)
async def start_voice_generation(
    request: VoiceGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Estimate the cost of a voice generation job.
    
    This endpoint estimates the cost of a voice generation job and checks if the user can afford it.
    """
    print(f"Starting voice generation for user {current_user.id} and book {request.book_id}")
    try:
        estimate = VoiceGenerationService.estimate_job_cost(db=db, chapters=request.chapters, user_id=current_user.id)
        can_afford = VoiceGenerationService.can_user_afford_job(db=db, job_estimate=estimate, user_id=current_user.id)
        return VoiceGenerationEstimateResponse(
            total_tokens=estimate["total_tokens"],
            total_cost=estimate["total_cost"],
            can_afford=can_afford
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to estimate voice generation job: {str(e)}"
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

@router.get("/generated-voices/{job_id}", response_model=List[ProcessedVoiceChunkResponse])
async def get_generated_voices(
    job_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the list of generated voices for a specific job.
    
    This endpoint retrieves all ProcessedVoiceChunks with type CHAPTER_AUDIO for the specified job,
    sorted in ascending order by index, and includes S3 public links for each voice file.
    """
    try:
        job = db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.id == job_id,
            BookVoiceProcessingJob.user_id == current_user.id,
            BookVoiceProcessingJob.is_deleted == False
        ).first()
        
        book = db.query(Book).filter(
            Book.id == job.book_id,
            Book.user_id == current_user.id,
            Book.is_deleted == False
        ).first()
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Query ProcessedVoiceChunks with type CHAPTER_AUDIO for this book
        voice_chunks = db.query(ProcessedVoiceChunks).filter(
            ProcessedVoiceChunks.book_id == job.book_id,
            ProcessedVoiceChunks.user_id == current_user.id,
            ProcessedVoiceChunks.type == ProcessedVoiceChunksType.CHAPTER_AUDIO,
            ProcessedVoiceChunks.is_deleted == False,
            ProcessedVoiceChunks.voice_processing_job_id == job_id
        ).order_by(ProcessedVoiceChunks.index.asc()).offset(skip).limit(limit).all()
        
        # Convert to response model with s3_links
        response_data = []
        for chunk in voice_chunks:
            chunk_data = ProcessedVoiceChunkResponse(
                id=chunk.id,
                s3_key=chunk.s3_key,
                s3_public_link=chunk.s3_public_link,  # Include the S3 public link
                index=chunk.index,
                chapter_id=chunk.chapter_id,
                data=chunk.data,
                created_at=chunk.created_at
            )
            response_data.append(chunk_data)
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve generated voices: {str(e)}"
        )

@router.get("/all-generated-voices", response_model=List[ProcessedVoiceChunkResponse])
async def get_all_generated_voices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all generated voices for the current user across all their books.
    
    This endpoint retrieves all ProcessedVoiceChunks with type CHAPTER_AUDIO for the current user,
    sorted in ascending order by index, and includes S3 public links for each voice file.
    """
    try:
        # Query ProcessedVoiceChunks with type CHAPTER_AUDIO for this user
        voice_chunks = db.query(ProcessedVoiceChunks).filter(
            ProcessedVoiceChunks.user_id == current_user.id,
            ProcessedVoiceChunks.type == ProcessedVoiceChunksType.CHAPTER_AUDIO,
            ProcessedVoiceChunks.is_deleted == False
        ).order_by(ProcessedVoiceChunks.index.asc()).offset(skip).limit(limit).all()
        
        # Convert to response model with s3_links
        response_data = []
        for chunk in voice_chunks:
            chunk_data = ProcessedVoiceChunkResponse(
                id=chunk.id,
                s3_key=chunk.s3_key,
                s3_public_link=chunk.s3_public_link,  # Include the S3 public link
                index=chunk.index,
                chapter_id=chunk.chapter_id,
                data=chunk.data,
                created_at=chunk.created_at
            )
            response_data.append(chunk_data)
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve generated voices: {str(e)}"
        )