from sqlalchemy.orm import Session
from models.book_voice_processing_job import BookVoiceProcessingJob
from models.processed_voice_chunks import ProcessedVoiceChunks
from models.book import Book
from models.user import User
from models.voice_job import JobStatus
from schemas.voice_generation import VoiceGenerationRequest, ChapterData
from typing import List, Optional
from fastapi import HTTPException, status
import json
import logging
from utils.message_publisher import publish_message
from core.config import settings

logger = logging.getLogger(__name__)

class VoiceGenerationService:
    @staticmethod
    def create_voice_generation_job(
        db: Session, 
        user_id: int, 
        request: VoiceGenerationRequest
    ) -> BookVoiceProcessingJob:
        """Create a new voice generation job for the given chapters"""
        
        # Verify the book belongs to the user
        book = db.query(Book).filter(
            Book.id == request.book_id,
            Book.user_id == user_id,
            Book.is_deleted == False
        ).first()
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Prepare job data
        job_data = [chapter.model_dump() for chapter in request.chapters]
        
        # Create the job
        job = BookVoiceProcessingJob(
            user_id=user_id,
            book_id=request.book_id,
            status=JobStatus.QUEUED,
            data=job_data
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Publish message to worker
        try:
            # Convert Pydantic models to dictionaries for JSON serialization
            audio_params_dict = None
            if request.audio_generation_params:
                audio_params_dict = request.audio_generation_params.model_dump()
            
            message_data = {
                "job_id": job.id,
                "user_id": user_id,
                "book_id": request.book_id,
                "voice_id": request.voice_id,
                "audio_generation_params": audio_params_dict
            }
            
            publish_message(
                queue_name=settings.VOICE_GENERATION_QUEUE,
                message=json.dumps(message_data)
            )
            
            logger.info(f"Published voice generation job {job.id} to worker")
            
        except Exception as e:
            logger.error(f"Failed to publish message to worker: {str(e)}")
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.result = {"error": f"Failed to publish to worker: {str(e)}"}
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start voice generation job"
            )
        
        return job
    
    @staticmethod
    def get_job_status(db: Session, job_id: int, user_id: int) -> Optional[BookVoiceProcessingJob]:
        """Get the status of a voice generation job"""
        return db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.id == job_id,
            BookVoiceProcessingJob.user_id == user_id,
            BookVoiceProcessingJob.is_deleted == False
        ).first()
    
    @staticmethod
    def get_user_jobs(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[BookVoiceProcessingJob]:
        """Get all voice generation jobs for a user"""
        return db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.user_id == user_id,
            BookVoiceProcessingJob.is_deleted == False
        ).order_by(BookVoiceProcessingJob.created_at.desc()).offset(skip).limit(limit).all()
