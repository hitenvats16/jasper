from ..base import BaseWorker
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models import (
    BookVoiceProcessingJob,
    ProcessedVoiceChunks,
    JobStatus,
    Voice,
    Book,
    BookVoiceProcessingJob,
    User,
    ProcessedVoiceChunksType,
    Config,
)
from core.config import settings
import logging
from datetime import datetime
import sys
from utils.s3 import load_file_from_s3, upload_file_to_s3
import os
from workers.audio_generation.generator import AudiobookGenerator
from workers.audio_generation.silence import create_silence_strategy
from workers.audio_generation.splitter import QuoteAwareTTSTextSplittingStrategy
from workers.audio_generation.tts import ChatterboxAudioStrategy
from services.credit_service import CreditService
from services.voice_generation_service import VoiceGenerationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class AudioGenerator(BaseWorker):
    def __init__(self):
        self.base_file_path = "temp_audio_generation"
        os.makedirs(self.base_file_path, exist_ok=True)

        logger.info(
            f"Initializing AudioGenerator with queue: {settings.VOICE_GENERATION_QUEUE}"
        )

        super().__init__(settings.VOICE_GENERATION_QUEUE)

    def generate_audio_for_chapter(
        self,
        chapter_data: dict,
        job: BookVoiceProcessingJob,
        user: User,
        book: Book,
        voice: Voice = None,
        audio_generation_params: dict = None,
        db: Session = None,
    ):
        """Generate audio for a specific chapter"""
        chapter_id = chapter_data.get("chapter_id")
        chapter_title = chapter_data.get("chapter_title")
        chapter_content = chapter_data.get("chapter_content")
        meta_data = chapter_data.get("meta_data", {})

        config = db.query(Config).filter(Config.user_id == user.id).first()

        # Note: Pick tts model dynamically based on the user's config later
        tts_model = ChatterboxAudioStrategy()

        # Use default silence strategy if config is not available
        if config and config.silence_strategy:
            silence_strategy = create_silence_strategy(
                config.silence_strategy, config.silence_data or {}
            )
        else:
            from workers.audio_generation.silence import AdaptiveSilenceStrategy

            silence_strategy = AdaptiveSilenceStrategy()

        audiobook_generator = AudiobookGenerator(
            audio_strategy=tts_model,
            chunking_strategy=QuoteAwareTTSTextSplittingStrategy(max_tokens=30),
            silence_strategy=silence_strategy,
        )

        logger.info(f"Generating audio for chapter {chapter_id}: {chapter_title}")

        try:
            # Generate audio using the audiobook generator
            params = audio_generation_params or {}
            audio_gen_params = {
                "exaggeration": params.get("exaggeration", 0.65),
                "temperature": params.get("temperature", 0.7),
                "cfg": params.get("cfg", 0.1),
                "seed": params.get(
                    "seed", 989443
                ),  # Deterministic seed based on chapter ID
            }

            # If voice_id is provided, try to get voice prompt
            if voice:
                try:
                    voice = (
                        db.query(Voice)
                        .filter(Voice.id == voice.id, Voice.is_deleted == False)
                        .first()
                    )
                    if voice and voice.s3_key:
                        audio_gen_params["audio_url"] = voice.s3_key
                        logger.info(f"Using voice sample for chapter {chapter_id}")
                except Exception as e:
                    logger.warning(f"Failed to load voice sample: {str(e)}")

            # Generate audio
            buffer = audiobook_generator.generate(
                large_text=chapter_content,
                audio_gen_params=audio_gen_params,
            )

            # Get file duration from the buffer first
            from pydub import AudioSegment

            buffer.seek(0)  # Reset buffer position
            audio = AudioSegment.from_wav(buffer)
            duration = len(audio) / 1000.0  # Convert to seconds

            # Reset buffer position for S3 upload
            buffer.seek(0)

            # Upload to S3
            filename = f"{chapter_id}_{job.id}.wav"
            s3_key = f"voice_chunks/{user.id}/{book.id}/{filename}"
            upload_file_to_s3(file_obj=buffer, custom_key=s3_key, filename=filename)

            return {
                "s3_key": s3_key,
                "duration": duration,
                "format": "audio/wav",
                "chapter_title": chapter_title,
                "meta_data": meta_data,
            }

        except Exception as e:
            logger.error(f"Failed to generate audio for chapter {chapter_id}: {str(e)}")
            raise

    def process(self, job_data: dict):
        """Process a voice generation job"""
        job_id = job_data.get("job_id")
        user_id = job_data.get("user_id")
        book_id = job_data.get("book_id")
        voice_id = job_data.get("voice_id")
        audio_generation_params = job_data.get("audio_generation_params", {})
        db = SessionLocal()

        if not job_id or not user_id or not book_id:
            logger.error(f"Invalid message format: {job_data}")
            return

        logger.info(
            f"Processing voice generation job {job_id} for user {user_id}, book {book_id}"
        )

        job = (
            self.db.query(BookVoiceProcessingJob)
            .filter(BookVoiceProcessingJob.id == int(job_id))
            .first()
        )

        # Estimate job cost
        job_estimate = VoiceGenerationService.estimate_job_cost(
            db=self.db, chapters=job.data, user_id=user_id
        )
        print(
            f"Job estimate: {job_estimate} for user {user_id} and book {book_id}"
        )
        # Check if user can afford job
        if not VoiceGenerationService.can_user_afford_job(
            db=self.db, job_estimate=job_estimate, user_id=user_id
        ):
            # update job status to failed
            self.update_job_status(
                job_id,
                "FAILED",
                {
                    "error": "Insufficient credits to start voice generation job",
                },
                db=db,
            )
            return
        
        # Prepare job data
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        book = self.db.query(Book).filter(Book.id == int(book_id)).first()
        voice = (
            (
                self.db.query(Voice)
                .filter(
                    Voice.id == voice_id,
                    Voice.is_deleted == False,
                    Voice.user_id == user_id,
                )
                .first()
            )
            if voice_id
            else None
        )

        if not job or not user or not book:
            logger.error(f"Job {job_id} not found")
            return

        try:
            # Update job status to processing
            self.update_job_status(
                job_id,
                "PROCESSING",
                {
                    "message": "Started processing chapters",
                    "total_chapters": len(job.data),
                },
            )

            processed_chapters = 0
            failed_chapters = 0

            # Process each chapter
            for index, chapter in enumerate(job.data):
                try:
                    logger.info(
                        f"Processing chapter {index + 1}/{len(job.data)}: {chapter.get('chapter_id')}"
                    )

                    # Generate audio for this chapter
                    result = self.generate_audio_for_chapter(
                        chapter_data=chapter,
                        job=job,
                        user=user,
                        book=book,
                        voice=voice,
                        audio_generation_params=audio_generation_params,
                        db=db,
                    )

                    # Create processed chunk record
                    self.create_processed_chunk(
                        job_id=job_id,
                        user_id=user_id,
                        book_id=book_id,
                        chapter_id=chapter.get("chapter_id"),
                        s3_key=result["s3_key"],
                        index=index,
                        data={
                            "chapter_title": result["chapter_title"],
                            "meta_data": result["meta_data"],
                            "duration": result["duration"],
                            "format": result["format"],
                            "processing_time": datetime.utcnow().isoformat(),
                        },
                        type=ProcessedVoiceChunksType.PARTIAL_AUDIO,
                        db=db,
                    )

                    processed_chapters += 1
                    logger.info(
                        f"Successfully processed chapter {chapter.get('chapter_id')}"
                    )

                except Exception as e:
                    failed_chapters += 1
                    logger.error(
                        f"Failed to process chapter {chapter.get('chapter_id')}: {str(e)}"
                    )
                    # Continue with other chapters even if one fails
                    continue

            # Update job status to completed
            if failed_chapters == 0:
                self.update_job_status(
                    job_id,
                    "COMPLETED",
                    {
                        "message": "Voice generation completed successfully",
                        "processed_chapters": processed_chapters,
                        "failed_chapters": failed_chapters,
                        "total_chapters": len(job.data),
                    },
                    db=db,
                )
                logger.info(f"Successfully completed voice generation job {job_id}")
            else:
                self.update_job_status(
                    job_id,
                    "COMPLETED",
                    {
                        "message": f"Voice generation completed with {failed_chapters} failed chapters",
                        "processed_chapters": processed_chapters,
                        "failed_chapters": failed_chapters,
                        "total_chapters": len(job.data),
                    },
                    db=db,
                )
                # Deduct credits from user
                CreditService.deduct_credit(
                    db=self.db,
                    user_id=user_id,
                    amount=job.credit_takes,
                    description=f"Voice generation job completed",
                )
                logger.warning(
                    f"Completed voice generation job {job_id} with {failed_chapters} failed chapters"
                )

        except Exception as e:
            logger.error(f"Error processing voice generation job {job_id}: {str(e)}")
            # Update job status to failed
            self.update_job_status(
                job_id,
                "FAILED",
                {
                    "error": str(e),
                    "processed_chapters": (
                        processed_chapters if "processed_chapters" in locals() else 0
                    ),
                    "failed_chapters": (
                        failed_chapters if "failed_chapters" in locals() else 0
                    ),
                },
                db=db,
            )

    def update_job_status(
        self, job_id: int, status: str, result: dict = None, db: Session = None
    ):
        """Update job status via API"""
        try:
            job = (
                db.query(BookVoiceProcessingJob)
                .filter(BookVoiceProcessingJob.id == job_id)
                .first()
            )
            if job:
                job.status = status
                db.commit()
                logger.info(f"Updated job {job_id} status to {status}")
            else:
                logger.warning(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Failed to update job status: {str(e)}")
            raise

    def create_processed_chunk(
        self,
        job_id: int,
        user_id: int,
        book_id: int,
        chapter_id: str,
        s3_key: str,
        index: int,
        type: ProcessedVoiceChunksType,
        data: dict = {},
        db: Session = None,
    ):
        """Create processed chunk record via API"""
        try:
            processed_chunk = ProcessedVoiceChunks(
                voice_processing_job_id=job_id,
                user_id=user_id,
                book_id=book_id,
                chapter_id=chapter_id,
                s3_key=s3_key,
                index=index,
                data=data,
                type=type,
            )
            db.add(processed_chunk)
            db.commit()
            logger.info(f"Created processed chunk for chapter {chapter_id}")
            return processed_chunk
        except Exception as e:
            logger.error(f"Failed to create processed chunk: {str(e)}")
            raise


if __name__ == "__main__":
    logger.info("Starting AudioGenerator worker...")
    generator = AudioGenerator()
    try:
        logger.info("Starting to consume messages...")
        generator.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        generator.close()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        generator.close()
