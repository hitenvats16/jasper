"""
Book Processing Service
Handles book processing operations and job management
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from models import Book, BookProcessingJob, JobStatus
from workers.base import BaseWorker
from core.config import settings

logger = logging.getLogger(__name__)

class BookProcessingService:
    def __init__(self):
        pass

    def create_processing_job(self, db: Session, book: Book) -> BookProcessingJob:
        """Create a new BookProcessingJob for a book"""
        try:
            # Validate inputs
            logger.info(f"Creating processing job - book type: {type(book)}, book value: {book}")
            
            if not book:
                logger.error("Book object is None or empty")
                raise ValueError("Book object is required")
            
            if not hasattr(book, 'id'):
                logger.error(f"Book object missing 'id' attribute. Type: {type(book)}")
                raise AttributeError(f"Book object missing 'id' attribute. Type: {type(book)}")
                
            if not hasattr(book, 'user_id'):
                logger.error(f"Book object missing 'user_id' attribute. Type: {type(book)}")
                raise AttributeError(f"Book object missing 'user_id' attribute. Type: {type(book)}")
            
            logger.info(f"Creating BookProcessingJob for book {book.id}, user {book.user_id}")
            
            processing_job = BookProcessingJob(
                user_id=book.user_id,
                book_id=book.id,
                status=JobStatus.QUEUED,
                processed_data={}
            )
            
            db.add(processing_job)
            db.flush()
            db.commit()
            
            logger.info(f"Created BookProcessingJob {processing_job.id} for book {book.id}")
            return processing_job
            
        except Exception as e:
            logger.error(f"Failed to create BookProcessingJob for book {getattr(book, 'id', 'unknown')}: {str(e)}")
            logger.error(f"Book object type: {type(book)}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def publish_job_to_queue(self, job: BookProcessingJob, book: Book) -> bool:
        """Publish a job to the TEXT_PARSER_QUEUE"""
        try:
            # Create a temporary worker instance to publish the message
            class TempWorker(BaseWorker):
                def __init__(self):
                    super().__init__(settings.TEXT_PARSER_QUEUE)
                
                def process(self, job_data):
                    pass  # Not used for publishing
            
            temp_worker = TempWorker()
            message = {
                "job_id": job.id,
                "book_id": book.id,
            }
            
            temp_worker.publish_message(message)
            logger.info(f"Published book processing job {job.id} to TEXT_PARSER_QUEUE")
            temp_worker.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to queue: {str(e)}")
            return False

    def create_and_publish_job(self, db: Session, book: Book) -> Optional[BookProcessingJob]:
        """Create a processing job and publish it to the queue"""
        try:
            # Create the job
            job = self.create_processing_job(db, book)
            
            # Commit the job to database FIRST
            db.commit()
            logger.info(f"Committed job {job.id} to database")
            
            # Publish the job to the queue
            self.publish_job_to_queue(job, book)

            return job
                
        except Exception as e:
            logger.error(f"Failed to create and publish job for book {book.id}: {str(e)}")
            db.rollback()
            return None

    def get_job_status(self, db: Session, job_id: int) -> Optional[BookProcessingJob]:
        """Get a BookProcessingJob by ID"""
        return db.query(BookProcessingJob).filter_by(id=job_id, is_deleted=False).first()

    def get_book_jobs(self, db: Session, book_id: int) -> list[BookProcessingJob]:
        """Get all processing jobs for a book"""
        return db.query(BookProcessingJob).filter_by(book_id=book_id, is_deleted=False).all()

    def cancel_job(self, db: Session, job_id: int) -> bool:
        """Cancel a processing job if it's still active"""
        job = self.get_job_status(db, job_id)
        if job and job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
            job.status = JobStatus.FAILED
            self._add_timeline_event(job, "job_cancelled", "Job was cancelled by user")
            db.commit()
            logger.info(f"Cancelled job {job_id}")
            return True
        return False

    def _add_timeline_event(self, job: BookProcessingJob, event: str, details: str, data: Dict[str, Any] = None):
        """Add a timeline event to the job's processed_data"""
        if not job.processed_data:
            job.processed_data = {"timeline": [], "page_processing": {}, "errors": [], "warnings": []}
        
        event_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "details": details
        }
        
        if data:
            event_entry["data"] = data
            
        job.processed_data["timeline"].append(event_entry) 