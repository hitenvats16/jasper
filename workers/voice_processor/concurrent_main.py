import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models import VoiceProcessingJob, JobStatus, Voice
from models.voice_embedding import VoiceEmbedding
from services.qdrant_service import QdrantService
from core.config import settings
import logging
import sys
import io
from utils.s3 import load_file_from_s3
from openvoice.api import ToneColorConverter
from openvoice import se_extractor
import os
import torch
import shutil
from .setup_checkpoints import setup_checkpoints
import pika
import json
from datetime import datetime
from .config import *

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class ThreadSafeVoiceProcessor:
    """Thread-safe wrapper for voice processing operations"""
    
    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.base_file_path = TEMP_DIR_PREFIX
        os.makedirs(self.base_file_path, exist_ok=True)
        
        # Each thread gets its own ToneColorConverter instance
        logger.info(f"Thread {thread_id}: Loading ToneColorConverter")
        self.ckpt_converter = os.path.join(os.path.dirname(os.path.abspath(__file__)), CHECKPOINT_DIR, f"checkpoints_{CHECKPOINT_VERSION}/{CHECKPOINT_SUBDIR}")
        
        # Device selection based on configuration
        if USE_CUDA and torch.cuda.is_available():
            self.device = CUDA_DEVICE
        else:
            self.device = CPU_DEVICE
            
        self.tone_color_converter = ToneColorConverter(f'{self.ckpt_converter}/config.json', device=self.device)
        self.tone_color_converter.load_ckpt(f'{self.ckpt_converter}/checkpoint.pth')
        logger.info(f"Thread {thread_id}: Tone Color Converter loaded on {self.device}")
        
        # Each thread gets its own Qdrant service instance
        self.qdrant_service = QdrantService()
        logger.info(f"Thread {thread_id}: Qdrant service initialized")

    def extract_tone_color(self, ref_speaker):
        """Extract tone color from reference speaker audio"""
        target_se, audio_name = se_extractor.get_se(ref_speaker, self.tone_color_converter, vad=True)
        return target_se

    def generate_voice_tone(self, job_data: dict):
        """Generate a voice tone for a given job"""
        job_id = job_data.get("job_id")
        s3_key = job_data.get("s3_key")
        voice_id = job_data.get("voice_id")
        metadata = job_data.get("metadata", {})

        logger.info(f"Thread {self.thread_id}: Processing voice tone - Job ID: {job_id}, S3 Key: {s3_key}, Voice ID: {voice_id}")
        buffer = io.BytesIO()
        load_file_from_s3(s3_key, buffer=buffer)
        buffer.seek(0)

        audio_data = buffer.read()

        # generating random file at /temp/{uuid} and temporarily saving audio there
        temp_dir = os.path.join(self.base_file_path, f"{TEMP_FILE_PREFIX}_{job_id}_voice_{voice_id}_thread_{self.thread_id}")
        os.makedirs(temp_dir, exist_ok=True)
        file_name = metadata.get("filename")
        file_name = f"{job_id}_{voice_id}_{file_name}" 
        temp_file_path = os.path.join(temp_dir, file_name)

        with open(temp_file_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Thread {self.thread_id}: Audio saved to {temp_file_path}")

        # extracting tone color
        target_se = self.extract_tone_color(temp_file_path)
        logger.info(f"Thread {self.thread_id}: Target SE tensor shape: {target_se.shape}")

        # Store embedding in Qdrant
        embedding = VoiceEmbedding.from_tensor(
            job_id=job_id,
            voice_id=voice_id,
            target_se=target_se
        )
        self.qdrant_service.store_embedding(embedding)

        # deleting temp file
        shutil.rmtree(temp_dir)

class ConcurrentVoiceProcessor:
    def __init__(self, max_workers=MAX_WORKERS):
        """
        Initialize the concurrent voice processor.
        
        Args:
            max_workers: Maximum number of concurrent workers (default: from config)
        """
        self.max_workers = max_workers
        
        # Thread-local storage for voice processors
        self.thread_local = threading.local()
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=THREAD_POOL_MAX_WORKERS)
        
        logger.info(f"Initializing ConcurrentVoiceProcessor with {max_workers} workers")
        logger.info(f"Queue: {settings.VOICE_PROCESSING_QUEUE}")
        
        # Setup checkpoints
        logger.info("Setting up checkpoints")
        if not setup_checkpoints():
            raise RuntimeError("Failed to setup checkpoints")
        
        # RabbitMQ connection
        self.connection = None
        self.channel = None
        self.connect()

    def get_thread_processor(self):
        """Get or create a thread-safe voice processor for the current thread"""
        if not hasattr(self.thread_local, 'processor'):
            thread_id = threading.current_thread().ident
            self.thread_local.processor = ThreadSafeVoiceProcessor(thread_id)
        return self.thread_local.processor

    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            connection_url = settings.RABBITMQ_URL
            parameters = pika.URLParameters(url=connection_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue
            self.channel.queue_declare(
                queue=settings.VOICE_PROCESSING_QUEUE,
                durable=True
            )
            
            # Set prefetch count to allow multiple messages to be processed concurrently
            self.channel.basic_qos(prefetch_count=RABBITMQ_PREFETCH_COUNT)
            
            logger.info(f"Successfully connected to RabbitMQ queue: {settings.VOICE_PROCESSING_QUEUE}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    def process_job(self, job_data: dict):
        """Process a voice processing job - this runs in a separate thread"""
        job_id = job_data.get("job_id")
        s3_key = job_data.get("s3_key")
        voice_id = job_data.get("voice_id")
        
        if not job_id or not s3_key:
            logger.error(f"Invalid message format: {job_data}")
            return False

        logger.info(f"Processing job {job_id} with data: {job_data}")
        db = SessionLocal()
        job = None
        
        try:
            # Get the job
            job = db.query(VoiceProcessingJob).filter_by(id=job_id, is_deleted=False).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            # Update job status to processing
            job.status = JobStatus.PROCESSING
            db.commit()
            
            # Get thread-safe processor and process the voice
            processor = self.get_thread_processor()
            processor.generate_voice_tone(job_data)
            
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
            return True
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            if job:
                try:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update job status: {str(commit_error)}")
            return False
        finally:
            db.close()

    def process_message(self, ch, method, properties, body):
        """
        Process a message from the queue - this runs in the main thread
        """
        try:
            message = json.loads(body)
            logger.info(f"Received message from queue {settings.VOICE_PROCESSING_QUEUE}: {message}")
            
            # Submit job to thread pool for concurrent processing
            future = self.executor.submit(self.process_job, message)
            
            # Store the future and delivery tag for later acknowledgment
            future.add_done_callback(
                lambda f, ch=ch, method=method: self.handle_job_completion(f, ch, method)
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Reject message and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def handle_job_completion(self, future, ch, method):
        """Handle job completion and acknowledge message"""
        try:
            success = future.result()
            if success:
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Successfully processed message from queue {settings.VOICE_PROCESSING_QUEUE}")
            else:
                # Reject message and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.error(f"Failed to process message from queue {settings.VOICE_PROCESSING_QUEUE}")
        except Exception as e:
            logger.error(f"Error in job completion handler: {str(e)}")
            # Reject message and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start(self):
        """Start consuming messages from the queue"""
        try:
            self.channel.basic_consume(
                queue=settings.VOICE_PROCESSING_QUEUE,
                on_message_callback=self.process_message
            )
            logger.info(f"Started consuming messages from queue: {settings.VOICE_PROCESSING_QUEUE}")
            logger.info(f"Concurrent processing with {self.max_workers} workers")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error consuming messages: {str(e)}")
            raise

    def close(self):
        """Close the RabbitMQ connection and shutdown thread pool"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection")
        
        # Shutdown thread pool
        self.executor.shutdown(wait=THREAD_POOL_SHUTDOWN_WAIT)
        logger.info("Shutdown thread pool")

if __name__ == "__main__":
    logger.info("Starting ConcurrentVoiceProcessor worker...")
    processor = ConcurrentVoiceProcessor(max_workers=MAX_WORKERS)
    try:
        logger.info("Starting to consume messages...")
        processor.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        processor.close()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        processor.close() 