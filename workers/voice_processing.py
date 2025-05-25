from .base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models.voice_job import VoiceProcessingJob, JobStatus
import json
import logging

logger = logging.getLogger(__name__)

class VoiceProcessingWorker(BaseWorker):
    def process(self, job_data: dict):
        """Process a voice processing job"""
        job_id = job_data["job_id"]
        db: Session = SessionLocal()
        job = db.query(VoiceProcessingJob).filter_by(id=job_id).first()
        if not job:
            db.close()
            return
        try:
            job.status = JobStatus.PROCESSING
            db.commit()
            s3_link = job.s3_link
            metadata = job.metadata or {}
            # Here you would add your voice processing logic
            logger.info(f"Processing voice from {s3_link} with metadata: {metadata}")
            # Simulate processing result
            # TODO: Add logic to preprocess voice
            result = {"message": "Voice processed successfully"}
            job.status = JobStatus.COMPLETED
            job.result = result
            db.commit()
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            db.commit()
        finally:
            db.close()

def process_message(ch, method, properties, body):
    """Callback function for processing RabbitMQ messages"""
    try:
        job_data = json.loads(body)
        worker = VoiceProcessingWorker()
        worker.process(job_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Reject the message and requeue it
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) 