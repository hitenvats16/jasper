from .base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models.voice_job import VoiceProcessingJob, JobStatus
from models.voice import Voice
from core.config import settings
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class VoiceProcessor(BaseWorker):
    def __init__(self):
        logger.info(f"Initializing VoiceProcessor with queue: {settings.VOICE_PROCESSING_QUEUE}")
        logger.info(f"RabbitMQ settings - Host: {settings.RABBITMQ_HOST}, Port: {settings.RABBITMQ_PORT}, VHost: {settings.RABBITMQ_VHOST}")
        super().__init__(settings.VOICE_PROCESSING_QUEUE)

    def generate_voice_tone(self, job_data: dict):
        """Generate a voice tone for a given job"""
        job_id = job_data.get("job_id")
        s3_link = job_data.get("s3_link")
        voice_id = job_data.get("voice_id")

        print(f"Job ID: {job_id}, S3 Link: {s3_link}, Voice ID: {voice_id}")
        

    def process(self, job_data: dict):
        """Process a voice processing job"""
        job_id = job_data.get("job_id")
        s3_link = job_data.get("s3_link")
        voice_id = job_data.get("voice_id")  # Optional, only present for create jobs
        
        if not job_id or not s3_link:
            logger.error(f"Invalid message format: {job_data}")
            return
        
        db = SessionLocal()
        try:
            job = db.query(VoiceProcessingJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update job status to processing
            job.status = JobStatus.PROCESSING
            db.commit()
            
            self.generate_voice_tone(job_data)
            
            # If this is a voice creation job, update the voice record
            if voice_id:
                voice = db.query(Voice).filter_by(id=voice_id).first()
                if voice:
                    # Update voice with processing results
                    current_metadata = voice.voice_metadata or {}
                    current_metadata.update({
                        "processed": True,
                        "processed_at": datetime.utcnow().isoformat(),
                        "processing_result": {"status": "success"}
                    })
                    voice.voice_metadata = current_metadata
                    db.commit()
            
            # Update job status to completed
            job.status = JobStatus.COMPLETED
            job.result = {
                "message": "Voice processing completed successfully",
                "voice_id": voice_id,
                "processed_at": datetime.utcnow().isoformat()
            }
            db.commit()
            
            logger.info(f"Successfully processed job {job_id}")
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            if job:
                job.status = JobStatus.FAILED
                job.error = str(e)
                db.commit()
        finally:
            db.close()

if __name__ == "__main__":
    logger.info("Starting VoiceProcessor worker...")
    processor = VoiceProcessor()
    try:
        logger.info("Starting to consume messages...")
        processor.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        processor.close()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        processor.close() 