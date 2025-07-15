from sqlalchemy.orm import Session
from models.book_voice_processing_job import BookVoiceProcessingJob
from models.processed_voice_chunks import ProcessedVoiceChunks
from models.book import Book
from models.user import User
from models.voice_job import JobStatus
from schemas.voice_generation import VoiceGenerationRequest, ChapterData
from typing import List, Optional, Union, Dict, Any
from fastapi import HTTPException, status
import json
import logging
from utils.message_publisher import publish_message
from core.config import settings
from services.rate_service import RateService
from utils.text import count_tokens
from services.credit_service import CreditService
from models.credit import UserCredit

logger = logging.getLogger(__name__)

class VoiceGenerationService:
    @staticmethod
    def create_voice_generation_job(
        db: Session, 
        user_id: int, 
        request: VoiceGenerationRequest
    ) -> BookVoiceProcessingJob:
        """Create a new voice generation job for the given chapters"""
        print(f"Creating voice generation job for user {user_id} and book {request.book_id}")
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
    def estimate_job_cost(db: Session, chapters: List[Union[ChapterData, Dict[str, Any]]], user_id: int) -> Dict[str, Any]:
        """Estimate the cost of a voice generation job"""
        rate = RateService.get_user_rate_value(db=db, user_id=user_id)
        total_tokens = 0
        for chapter in chapters:
            if isinstance(chapter, ChapterData):
                total_tokens += count_tokens(chapter.chapter_content)
            else:
                total_tokens += count_tokens(chapter.get("chapter_content", ""))
        return {
            "total_tokens": total_tokens,
            "total_cost": total_tokens * rate
        }
    
    @staticmethod
    def can_user_afford_job(db: Session, job_estimate: dict, user_id: int) -> bool:
        """Check if a user can afford a voice generation job"""
        user_credit = CreditService.get_or_create_user_credit(db, user_id)
        user_credit = user_credit.balance

        # Get processing or in queue jobs and sum up credits
        processing_jobs = db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.user_id == user_id,
            BookVoiceProcessingJob.status.in_([JobStatus.PROCESSING, JobStatus.QUEUED])
        ).all()

        total_credits = sum([job.credit_takes for job in processing_jobs]) + job_estimate["total_cost"]
        print(f"Total credits: {total_credits}, user credit: {user_credit}")
        return user_credit >= total_credits
    
    @staticmethod
    def get_job_status(db: Session, job_id: int, user_id: int) -> Optional[BookVoiceProcessingJob]:
        """Get the status of a voice generation job"""
        return db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.id == job_id,
            BookVoiceProcessingJob.user_id == user_id,
            BookVoiceProcessingJob.is_deleted == False
        ).first()
    
    @staticmethod
    def get_user_jobs(db: Session, user_id: int, skip: int = 0, limit: int = 100, project_id: int = None) -> List[BookVoiceProcessingJob]:
        """Get voice generation jobs for a user, optionally filtered by project"""
        query = db.query(BookVoiceProcessingJob).filter(
            BookVoiceProcessingJob.user_id == user_id,
            BookVoiceProcessingJob.is_deleted == False
        )
        
        # If project_id is provided, join with Book and filter by project
        if project_id is not None:
            from models.book import Book, book_project_association
            query = query.join(Book, BookVoiceProcessingJob.book_id == Book.id).join(
                book_project_association, Book.id == book_project_association.c.book_id
            ).filter(
                book_project_association.c.project_id == project_id,
                Book.is_deleted == False
            )
        
        return query.order_by(BookVoiceProcessingJob.created_at.desc()).offset(skip).limit(limit).all()
