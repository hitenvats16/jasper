from ..base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models import VoiceProcessingJob, JobStatus, Voice
from models.voice_embedding import VoiceEmbedding
from services.qdrant_service import QdrantService
from core.config import settings
import logging
from datetime import datetime
import sys
import io
from utils.s3 import load_file_from_s3
from openvoice.api import ToneColorConverter
from openvoice import se_extractor
import os
import torch
import shutil
from .setup_checkpoints import setup_checkpoints

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
        self.base_file_path = "temp_voices"
        os.makedirs(self.base_file_path, exist_ok=True)

        logger.info(f"Initializing VoiceProcessor with queue: {settings.VOICE_PROCESSING_QUEUE}")
        
        # Setup checkpoints
        logger.info("Setting up checkpoints")
        if not setup_checkpoints():
            raise RuntimeError("Failed to setup checkpoints")
        
        logger.info("Loading ToneColorConverter")
        self.ckpt_converter = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoints", "checkpoints_v2/converter")
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.tone_color_converter = ToneColorConverter(f'{self.ckpt_converter}/config.json', device=self.device)
        self.tone_color_converter.load_ckpt(f'{self.ckpt_converter}/checkpoint.pth')

        logger.info("Tone Color Converter loaded")
        logger.info(f"Device: {self.device}")

        logger.info("Initializing Qdrant service")
        # Initialize Qdrant service
        self.qdrant_service = QdrantService()
        logger.info("Qdrant service initialized")
        
        super().__init__(settings.VOICE_PROCESSING_QUEUE)

    def extract_tone_color(self, ref_speaker):
        target_se, audio_name = se_extractor.get_se(ref_speaker, self.tone_color_converter, vad=True)
        return target_se

    def generate_voice_tone(self, job_data: dict):
        """Generate a voice tone for a given job"""
        job_id = job_data.get("job_id")
        s3_key = job_data.get("s3_link")
        voice_id = job_data.get("voice_id")
        metadata = job_data.get("metadata", {})

        logger.info(f"Processing voice tone - Job ID: {job_id}, S3 Key: {s3_key}, Voice ID: {voice_id}")
        buffer = io.BytesIO()
        load_file_from_s3(s3_key, buffer=buffer)
        buffer.seek(0)

        audio_data = buffer.read()

        # generating random file at /temp/{uuid} and temporarily saving audio there
        temp_dir = os.path.join(self.base_file_path, f"job_{job_id}_voice_{voice_id}")
        os.makedirs(temp_dir, exist_ok=True)
        file_name = metadata.get("filename")
        file_name = f"{job_id}_{voice_id}_{file_name}" 
        temp_file_path = os.path.join(temp_dir, file_name)

        with open(temp_file_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Audio saved to {temp_file_path}")

        # extracting tone color
        target_se = self.extract_tone_color(temp_file_path)
        logger.info(f"Target SE tensor shape: {target_se.shape}")

        # Store embedding in Qdrant
        embedding = VoiceEmbedding.from_tensor(
            job_id=job_id,
            voice_id=voice_id,
            target_se=target_se
        )
        self.qdrant_service.store_embedding(embedding)

        # deleting temp file
        shutil.rmtree(temp_dir)

    def process(self, job_data: dict):
        """Process a voice processing job"""
        job_id = job_data.get("job_id")
        s3_link = job_data.get("s3_link")
        voice_id = job_data.get("voice_id")  # Optional, only present for create jobs
        
        if not job_id or not s3_link:
            logger.error(f"Invalid message format: {job_data}")
            return

        logger.info(f"Processing job {job_id} with data: {job_data}")
        db = SessionLocal()
        job = None
        
        try:
            # Get the job
            job = db.query(VoiceProcessingJob).filter_by(id=job_id, is_deleted=False).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Update job status to processing
            job.status = JobStatus.PROCESSING
            db.commit()
            
            # Process the voice
            self.generate_voice_tone(job_data)
            
            # If this is a voice creation job, update the voice record
            if voice_id:
                voice = db.query(Voice).filter_by(id=voice_id, is_deleted=False).first()
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
                try:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update job status: {str(commit_error)}")
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