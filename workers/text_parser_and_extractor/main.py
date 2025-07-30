from ..base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models import BookProcessingJob, Book, JobStatus
from workers.text_parser_and_extractor.parsers.pdf import PDFParser
from core.config import settings
import logging
from datetime import datetime
import sys
import os
import json
from utils.s3 import load_file_from_s3
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TextParserAndExtractor(BaseWorker):
    def __init__(self):
        # Initialize PDF parser for book processing
        self.pdf_parser = PDFParser()

        logger.info(f"Initializing TextParserAndExtractor with queue: {settings.TEXT_PARSER_QUEUE}")
        
        super().__init__(settings.TEXT_PARSER_QUEUE)

    def process(self, job_data: dict):
        """Process a job from the TEXT_PARSER_QUEUE"""
        job_id = job_data.get("job_id")
        book_id = job_data.get("book_id")
        
        # Determine job type based on message format
        if book_id:
            # This is a book processing job
            self._process_book_job(job_data)
        elif job_id and 's3_key' in job_data and 'file_type' in job_data:
            # This is a legacy text parsing job
            self._process_text_parsing_job(job_data)
        else:
            logger.error(f"Invalid message format: {job_data}")
            return

    def _process_book_job(self, job_data: dict):
        """Process a book processing job"""
        job_id = job_data.get("job_id")
        book_id = job_data.get("book_id")
        
        logger.info(f"Processing book processing job {job_id} for book {book_id}")
        logger.info(f"Job data received: {job_data}")
        
        db = SessionLocal()
        job = None
        book = None
        
        try:
            # Get the job and book from database
            job = db.query(BookProcessingJob).filter_by(id=job_id, is_deleted=False).first()
            logger.info(f"Job query result: {job}")
            
            if not job:
                logger.error(f"BookProcessingJob {job_id} not found")
                return
                
            book = db.query(Book).filter_by(id=book_id, is_deleted=False).first()
            if not book:
                logger.error(f"Book {book_id} not found")
                return

            # Check if job status is not QUEUED (safety check)
            if job.status != JobStatus.QUEUED:
                logger.warning(f"Rejecting book processing job {job_id} with not QUEUED status - job not ready for processing")
                return

            # Update job status to processing
            job.status = JobStatus.PROCESSING
            job.data = {
                "timeline": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "job_started",
                        "details": "Book processing started"
                    }
                ],
                "page_processing": {},
                "errors": [],
                "warnings": []
            }
            db.commit()
            
            # Get S3 key from book record
            s3_key = book.s3_key
            if not s3_key:
                logger.error(f"No S3 key found for book {book_id}")
                raise Exception("No S3 key found for book")
            
            logger.info(f"Loading file from S3: {s3_key}")
            pdf_buffer = io.BytesIO()
            load_file_from_s3(s3_key, buffer=pdf_buffer)
            pdf_buffer.seek(0, os.SEEK_END)
            pdf_size = pdf_buffer.tell()
            pdf_buffer.seek(0)

            job.data["timeline"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "event": "file_loaded",
                "details": f"Loaded file from S3: {s3_key} ({pdf_size} bytes)"
            })

            # Parse the PDF
            logger.info(f"Starting PDF parsing for book {book_id}")
            
            book_structure = self.pdf_parser.parse(
                pdf_buffer=pdf_buffer,
                book_id=str(book_id),
                book_title=book.title,
                author=book.author
            )
            
            # Convert book structure to dict for storage
            book_structure_dict = book_structure.model_dump()
            
            # Update job with results
            job.status = JobStatus.COMPLETED
            job.processed_data = book_structure_dict
            job.book_id = book_id
            
            # Add completion timeline event
            job.result = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "parsing_completed",
                "details": f"Successfully parsed {len(book_structure.chapters)} chapters with {sum(len(ch.sections) for ch in book_structure.chapters)} sections"
            }
            
            # Update book data with parsed structure
            book.data = book_structure_dict
            
            db.commit()
            logger.info(f"Successfully processed book {book_id} with {len(book_structure.chapters)} chapters")
            
        except Exception as e:
            logger.error(f"Error processing book {book_id}: {str(e)}")
            if job:
                try:
                    job.status = JobStatus.FAILED
                    job.result ={
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": str(e),
                        "details": "Book processing failed"
                    }
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update job status: {str(commit_error)}")
        finally:
            db.close()

if __name__ == "__main__":
    logger.info("Starting TextParserAndExtractor worker...")
    parser = TextParserAndExtractor()
    try:
        logger.info("Starting to consume messages...")
        parser.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        parser.close()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        parser.close()
