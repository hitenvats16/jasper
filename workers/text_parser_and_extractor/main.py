from ..base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models import TextParsingJob, JobStatus
from core.config import settings
import logging
from datetime import datetime
import sys
import io
from utils.s3 import load_file_from_s3, upload_file_to_s3
import os
import shutil
import json

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
        self.base_file_path = "temp_text_parsing"
        os.makedirs(self.base_file_path, exist_ok=True)

        logger.info(f"Initializing TextParserAndExtractor with queue: {settings.TEXT_PARSER_QUEUE}")
        
        # TODO: Initialize text parsing models/services here
        # Example: self.ocr_model = load_ocr_model()
        # Example: self.text_extractor = TextExtractor()
        # Example: self.nlp_processor = NLPProcessor()
        
        super().__init__(settings.TEXT_PARSER_QUEUE)

    def process(self, job_data: dict):
        """Process a text parsing and extraction job"""
        job_id = job_data.get("job_id")
        s3_link = job_data.get("s3_link")
        file_type = job_data.get("file_type")
        
        if not job_id or not s3_link or not file_type:
            logger.error(f"Invalid message format: {job_data}")
            return

        logger.info(f"Processing text parsing job {job_id} with data: {job_data}")
        db = SessionLocal()
        job = None
        
        try:
            # TODO: Get the job from database
            # Example: job = db.query(TextParsingJob).filter_by(id=job_id, is_deleted=False).first()
            # if not job:
            #     logger.error(f"Job {job_id} not found")
            #     return

            # TODO: Update job status to processing
            # Example: job.status = JobStatus.PROCESSING
            # Example: db.commit()
            
            # Parse and extract text
            
            # TODO: Update job status to completed with results
            # Example: job.status = JobStatus.COMPLETED
            # Example: job.result = {
            #     "message": "Text parsing and extraction completed successfully",
            #     "extracted_text": result["extracted_text"][:1000],  # Store first 1000 chars
            #     "s3_key": result["s3_key"],
            #     "word_count": result["word_count"],
            #     "confidence_score": result["confidence_score"],
            #     "entities_count": len(result["entities"]),
            #     "has_summary": bool(result["summary"]),
            #     "processed_at": datetime.utcnow().isoformat()
            # }
            # Example: db.commit()
            
            logger.info(f"Successfully processed text parsing job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing text parsing job {job_id}: {str(e)}")
            if job:
                try:
                    # TODO: Update job status to failed
                    # Example: job.status = JobStatus.FAILED
                    # Example: job.error = str(e)
                    # Example: db.commit()
                    pass
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
