from ..base import BaseWorker
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from db.session import SessionLocal
from models import (
    User,
    JobStatus,
    AudioGenerationJob,
    Voice,
    Config,
    AudiobookGeneration,
    AudiobookType,
)
from core.config import settings
import logging
import sys
from utils.s3 import load_file_from_s3, upload_file_to_s3
from workers.audio_generation.silence import create_silence_strategy, SilencingStrategies
from workers.audio_generation.tts import MinimaxAudioStrategy
from services.credit_service import CreditService
import traceback
from utils.audio_generation import estimate_job_cost, can_user_afford_job
import json
from typing import Optional, Dict, List
from schemas.book import ChapterCommand
from utils.text import split_content_by_commands
from workers.audio_generation.splitter import QuoteAwareTTSTextSplittingStrategy
import numpy as np
from pydub import AudioSegment
import io
from scipy.io.wavfile import write as wav_write
from workers.audio_generation.sts import ChatterboxSTS
import uuid
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

class AudioGenerator(BaseWorker):
    def __init__(self):
        # Pass max_retries to BaseWorker (set to 2 for voice generation as it's expensive)
        super().__init__(settings.VOICE_GENERATION_QUEUE, max_retries=2)

    def generate_audio_for_chapter(
        self,
        chapter_data: dict,
        job: AudioGenerationJob,
        user: User,
        voice: Voice = None,
        audio_generation_params: dict = None,
        config: Optional[Dict[str, List[ChapterCommand]]] = None,
        db: Session = None,
    ) -> io.BytesIO:
        logger = logging.getLogger(__name__)
        logger = logging.getLogger(__name__)
        logger.info(
            f"[AudioGenerationWorker]. user_id={user.id}, job_id={job.id}"
        )
        """Generate audio for a specific chapter"""
        """This will parse the text and generate audio for the chapter"""
        if config is None:
            config = {}

        audio_gen_params = {}
        if audio_generation_params:
            audio_gen_params.update(audio_generation_params)

        silence_strategy_type = user.config.silence_strategy if user.config else SilencingStrategies.FIXED_SILENCING.value
        silence_data = user.config.silence_data if user.config else {}

        silence_strategy = create_silence_strategy(silence_strategy_type, silence_data)
        splitted_content = split_content_by_commands(chapter_data, config)
        logger.info(f"[AudioGenerator] The splitted content: {splitted_content}")
        audio_strategy = MinimaxAudioStrategy()
        chunking_strategy = QuoteAwareTTSTextSplittingStrategy(max_tokens=500)

        sts_strategy = ChatterboxSTS()
        cnt = 0

        all_audio_arrays = []
        successful_chunks = 0
        for index, chunk in enumerate(splitted_content):
            text_content = chunk.get("content")
            part_voice_id = chunk.get("voice_id")
            emotion = chunk.get("emotion")
            
            if emotion: 
                audio_gen_params["voice_settings"]["emotion"] = emotion

            text_chunks_with_metadata = list(chunking_strategy.chunk_stream(text_content))

            for i, (chunk_text, is_paragraph_end) in enumerate(text_chunks_with_metadata):
                cnt += 1
                logger.info(f"Generating audio for chunk {index} {i+1} of {len(text_chunks_with_metadata)}")
                
                tts_result = audio_strategy.generate_audio(
                    chunk_text, audio_generation_params=audio_gen_params
                )

                chunk_buffer = tts_result.get("audio_buffer")
                file_extension = tts_result.get("file_extension")

                if chunk_buffer and chunk_buffer.getbuffer().nbytes > 0:
                    # Convert BytesIO buffer to numpy array for processing
                    chunk_buffer.seek(0)
                    voice_id = voice.id
                    # Applying voice to the chunk
                    if part_voice_id is not None:
                        voice_id = part_voice_id

                    voice = db.query(Voice).filter(Voice.id == voice_id).first()

                    if voice is not None:
                        sts_result = sts_strategy.transform(chunk_buffer, voice.s3_public_link, {
                            "source_audio_file_name": f"{uuid.uuid4()}.{file_extension}"
                        })
                        chunk_buffer = sts_result.get("audio_buffer")
                        file_extension = sts_result.get("file_extension")

                    chunk_buffer.seek(0)

                    # Create a copy of the buffer for audio processing (before S3 upload)
                    chunk_buffer_copy = io.BytesIO(chunk_buffer.getvalue())
                    chunk_buffer_copy.seek(0)

                    # Saving the chunk buffer to s3 and creating a db entry
                    file_name = f"{cnt}_{uuid.uuid4()}.{file_extension}"
                    s3_key = f"audio_chunks/{job.id}/{cnt}_{uuid.uuid4()}.{file_extension}"
                    upload_file_to_s3(chunk_buffer, filename=file_name, custom_key=s3_key)
                    
                    logger.info(f"[AudioGenerator] The final chunk uploaded to S3: {file_name}")
                    
                    # Load audio with proper format detection (don't assume wav)
                    chunk_audio_segment = AudioSegment.from_file(chunk_buffer_copy)
                    logger.info(f"[AudioGenerator] The chunk audio segment: {chunk_audio_segment}")
                    # Get the original sample rate from the audio segment
                    original_sample_rate = chunk_audio_segment.frame_rate
                    logger.info(f"Original audio sample rate: {original_sample_rate} Hz")

                    # Resample if necessary to match output sample rate
                    if original_sample_rate != audio_gen_params.get("audio_settings", {}).get("sample_rate", 16000):
                        logger.info(f"Resampling from {original_sample_rate} Hz to {audio_gen_params.get('audio_settings', {}).get('sample_rate', 16000)} Hz")
                        chunk_audio_segment = chunk_audio_segment.set_frame_rate(
                            audio_gen_params.get("audio_settings", {}).get("sample_rate", 16000)
                        )

                    # Convert to numpy array with proper normalization
                    chunk_wav_data = np.array(
                        chunk_audio_segment.get_array_of_samples(), dtype=np.int16
                    )

                    # Add pause audio to the current chunk buffer
                    if i < len(text_chunks_with_metadata) - 1:  # Don't add silence after the very last chunk
                        # Use silence strategy
                        silence_ms = silence_strategy.get_silence_duration(
                            chunk_text, is_paragraph_end
                        )   
                        logger.info(f"  - Adding {silence_ms}ms silence to chunk buffer.")

                        silence_samples = int(silence_ms * self.output_sample_rate / 1000)
                        if silence_samples > 0:
                            silence_buffer = np.zeros(silence_samples, dtype=np.int16)
                            # Concatenate the chunk audio with silence
                            chunk_wav_data = np.concatenate(
                                [chunk_wav_data, silence_buffer]
                            )

                    all_audio_arrays.append(chunk_wav_data)
                    successful_chunks += 1
            
            if successful_chunks == 0:
                logger.error(f"No successful chunks generated for chapter {chapter_data.get('chapter_id')}")
                continue
            
            # Combine all audio arrays into a single numpy array
        combined_audio_array = np.concatenate(all_audio_arrays)

        final_buffer = io.BytesIO()
        wav_write(final_buffer, audio_gen_params.get("audio_settings", {}).get("sample_rate", 16000), combined_audio_array)
        final_buffer.seek(0)

        return final_buffer


    def process(self, job_data: dict):
        """Process a voice generation job"""
        job_id = job_data.get("job_id")

        db = None
        try:
            # Create database session with explicit error handling
            try:
                db = SessionLocal()
                logger.info(f"Database session created for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to create database session: {str(e)}")
                raise RuntimeError(f"Database connection failed: {str(e)}")
        
            job = (
                db.query(AudioGenerationJob)
                .filter(AudioGenerationJob.id == int(job_id))
                .first()
            )

            if not job:
                raise ValueError(f"Job {job_id} not found in database")

            # Check if job status is not QUEUED (safety check)
            if job.status != JobStatus.QUEUED:
                logger.warning(f"Rejecting voice generation job {job_id} with not QUEUED status - job not ready for processing")
                return

            # Get book data from S3
            import io
            book_data_buffer = io.BytesIO()
            load_file_from_s3(job.input_data_s3_key, book_data_buffer)
            book_data_buffer.seek(0)
            logger.info(f"Book data buffer: {book_data_buffer}")
            book_data = json.load(book_data_buffer)

            # Estimate job cost
            try:
                job_estimate = estimate_job_cost(
                    db=db, chapters=book_data.get("chapters", []), user_id=job.user_id
                )
                logger.info(f"Job estimate: {job_estimate} for user {job.user_id}")
            except Exception as e:
                logger.error(f"Failed to estimate job cost: {str(e)}")
                raise RuntimeError(f"Cost estimation failed: {str(e)}")

            # Check if user can afford job
            try:
                if not can_user_afford_job(
                    db=db, job_estimate=job_estimate, user_id=job.user_id
                ):
                    logger.error(f"User {job.user_id} cannot afford job {job_id}")
                    self.update_job_status(
                        job_id,
                        "FAILED",
                        {
                            "error": "Insufficient credits to start voice generation job",
                            "required_credits": job_estimate.get("total_cost"),
                        },
                        db=db,
                    )
                    return
            except Exception as e:
                logger.error(f"Failed to check user affordability: {str(e)}")
                raise RuntimeError(f"Credit check failed: {str(e)}")
        
            # Prepare job data
            try:
                user = db.query(User).filter(User.id == int(job.user_id)).first()
                voice = (
                    (
                        db.query(Voice)
                        .filter(
                            Voice.id == job.voice_id,
                            Voice.is_deleted == False,
                            Voice.user_id == job.user_id,
                        )
                        .first()
                    )
                    if job.voice_id
                    else None
                )

                if not user:
                    raise ValueError(f"User {job.user_id} not found")

            except Exception as e:
                logger.error(f"Failed to load job entities: {str(e)}")
                raise ValueError(f"Failed to load required entities: {str(e)}")

            try:
                # Update job status to processing
                self.update_job_status(
                    job_id,
                    "PROCESSING",
                    {
                        "message": "Started processing chapters",
                        "total_chapters": len(book_data.get("chapters", [])),
                    },
                    db=db,
                )
                # Update job credit takes and total tokens
                job.total_cost = job_estimate.get("total_cost")
                job.total_tokens = job_estimate.get("total_tokens")
                db.commit()
                db.refresh(job)
                
                processed_chapters = 0
                failed_chapters = 0

                full_audio_buffer = io.BytesIO()

                # Process each chapter
                for index, chapter in enumerate(book_data.get("chapters", [])):
                    try:
                        logger.info(
                            f"Processing chapter {index + 1}/{len(book_data.get('chapters', []))}: {chapter.get('chapter_id')}"
                        )

                        # Generate audio for this chapter
                        audio_buffer = self.generate_audio_for_chapter(
                            chapter_data=chapter,
                            job=job,
                            user=user,
                            voice=voice,
                            audio_generation_params=job.job_metadata.get("voice_gen_params"),
                            config=book_data.get("config", {}),
                            db=db
                        )

                        # Get buffer information before uploading
                        audio_buffer.seek(0)
                        buffer_size = audio_buffer.getbuffer().nbytes
                        sample_rate = job.job_metadata.get("voice_gen_params", {}).get("audio_settings", {}).get("sample_rate", 16000)
                        duration = buffer_size / (2 * sample_rate)
                        audio_data = audio_buffer.getvalue()
                        
                        # Upload audio to s3
                        file_name = f"{chapter.get('chapter_id')}.wav"
                        s3_key = f"audio_generation/{job.id}/{file_name}"
                        upload_file_to_s3(audio_buffer, filename=file_name, custom_key=s3_key)

                        # Create audiobook generation entry
                        audiobook_generation = AudiobookGeneration(
                            project_id=job.project_id,
                            user_id=job.user_id,
                            key=file_name,
                            s3_key=s3_key,
                            type=AudiobookType.CHAPTERWISE_AUDIO,
                            index=index,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                            audio_generation_job_id=job.id,
                            data={
                                "title": book_data.get("title", "full_audio"),
                                "author": book_data.get("author", ""),
                                "narrator": voice.name,
                                "duration": duration,
                                "size_bytes": buffer_size,
                            }
                        )
                        db.add(audiobook_generation)
                        db.commit()
                        db.refresh(audiobook_generation)

                        # Add audio data to the full audio buffer
                        full_audio_buffer.write(audio_data)

                        # Add silence to the full audio buffer
                        silence_ms = 500 # 500ms silence between chapters (TODO: make it configurable)
                        silence_samples = int(silence_ms * job.job_metadata.get("voice_gen_params").get("audio_settings", {}).get("sample_rate", 16000) / 1000)
                        silence_buffer = np.zeros(silence_samples, dtype=np.int16)
                        full_audio_buffer.write(silence_buffer)

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
                
                # Get buffer information before uploading
                full_audio_buffer.seek(0)
                buffer_size = full_audio_buffer.getbuffer().nbytes
                sample_rate = job.job_metadata.get("voice_gen_params", {}).get("audio_settings", {}).get("sample_rate", 16000)
                duration = buffer_size / (2 * sample_rate)
                
                # Upload full audio to s3
                file_name = f"{book_data.get('title', 'full_audio')}.wav"
                s3_key = f"audio_generation/{job.id}/{file_name}"
                upload_file_to_s3(full_audio_buffer, filename=file_name, custom_key=s3_key)

                # Create audiobook generation entry
                audiobook_generation = AudiobookGeneration(
                    project_id=job.project_id,
                    user_id=job.user_id,
                    key=file_name,
                    s3_key=s3_key,
                    type=AudiobookType.FULL_AUDIO,
                    index=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    audio_generation_job_id=job.id,
                    data={
                        "title": book_data.get("title", "full_audio"),
                        "author": book_data.get("author", ""),
                        "narrator": voice.name,
                        "duration": duration,
                        "size_bytes": buffer_size,
                    }
                )
                db.add(audiobook_generation)
                db.commit()
                db.refresh(audiobook_generation)

                logger.info(f"Successfully uploaded full audio to s3 for voice generation job {job_id}")

                # Update job status to completed
                if failed_chapters == 0:
                    self.update_job_status(
                        job_id,
                        JobStatus.COMPLETED,
                        {
                            "message": "Voice generation completed successfully",
                            "processed_chapters": processed_chapters,
                            "failed_chapters": failed_chapters,
                            "total_chapters": len(book_data.get("chapters", [])),
                        },
                        db=db,
                    )
                    logger.info(f"Successfully completed voice generation job {job_id}")
                else:
                    self.update_job_status(
                        job_id,
                        JobStatus.COMPLETED,
                        {
                            "message": f"Voice generation completed with {failed_chapters} failed chapters",
                            "processed_chapters": processed_chapters,
                            "failed_chapters": failed_chapters,
                            "total_chapters": len(book_data.get("chapters", [])),
                        },
                        db=db,
                    )
                    logger.warning(
                        f"Completed voice generation job {job_id} with {failed_chapters} failed chapters"
                    )

                # Deduct credits from user
                try:
                    logger.info(f"Deducting credits from user {job.user_id} for job {job_id}")
                    CreditService.deduct_credit(
                        db=db,
                        user_id=job.user_id,
                        amount=job.total_cost,
                        description=f"Voice generation job completed",
                    )
                    logger.info(f"{job.total_cost} credits deducted from user {user_id} for job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to deduct credits: {str(e)}")
                    # Don't fail the entire job if credit deduction fails
                    # The job completed successfully, credit issue can be handled separately

            except Exception as e:
                logger.error(f"Error processing voice generation job {job_id}: {str(e)}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Update job status to failed
                try:
                    self.update_job_status(
                        job_id,
                        JobStatus.FAILED,
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "processed_chapters": (
                                processed_chapters if "processed_chapters" in locals() else 0
                            ),
                            "failed_chapters": (
                                failed_chapters if "failed_chapters" in locals() else 0
                            ),
                        },
                        db=db,
                    )
                except:
                    logger.error("Failed to update job status after processing error")
                raise

        except OperationalError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise RuntimeError(f"Database connection failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error in process method: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

        finally:
            # Always close the database session
            if db:
                try:
                    db.close()
                    logger.info("Database session closed")
                except Exception as e:
                    logger.error(f"Error closing database session: {str(e)}")

    def update_job_status(
        self, job_id: int, status: JobStatus, result: dict = None, db: Session = None
    ):
        """Update job status via API"""
        try:
            job = (
                db.query(AudioGenerationJob)
                .filter(AudioGenerationJob.id == job_id)
                .first()
            )
            if job:
                job.status = status
                if result:
                    job.result = result
                db.commit()
                logger.info(f"Updated job {job_id} status to {status}")
            else:
                logger.warning(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Failed to update job status: {str(e)}")
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
