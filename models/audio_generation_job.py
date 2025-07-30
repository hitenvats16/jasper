from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum, func, event, Float
from sqlalchemy.orm import relationship
from db.session import Base
from models.job_status import JobStatus
from utils.s3 import get_presigned_url
from utils.queue_publisher import publish_to_queue
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class AudioGenerationJob(Base):
    __tablename__ = "audio_generation_job"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    voice_id = Column(Integer, ForeignKey("voice.id"), nullable=False)
    input_data_s3_key = Column(String, nullable=False)
    job_metadata = Column(JSON, nullable=True)  # Renamed from metadata to avoid SQLAlchemy conflict
    result = Column(JSON, nullable=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    total_cost = Column(Float, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audio_generation_jobs", lazy="select")
    project = relationship("Project", back_populates="audio_generation_jobs", lazy="select")
    voice = relationship("Voice", back_populates="audio_generation_jobs", lazy="select")
    audio_chunks = relationship("AudioChunk", back_populates="audio_generation_job", lazy="select", cascade="all, delete-orphan")
    audiobook_generations = relationship("AudiobookGeneration", back_populates="audio_generation_job", lazy="select", cascade="all, delete-orphan") 

    @property
    def s3_url(self):
        return get_presigned_url(self.input_data_s3_key)
    
    def on_create_trigger(self):
        """Trigger method called when a new AudioGenerationJob is created"""
        logger.info(f"AudioGenerationJob created: ID={self.id}, User={self.user_id}, Status={self.status}")
        
        # Publish job ID to VOICE_GENERATION_QUEUE
        message = {"job_id": self.id}
        publish_to_queue(settings.VOICE_GENERATION_QUEUE, message)


# SQLAlchemy event listeners for triggers
@event.listens_for(AudioGenerationJob, 'after_insert')
def trigger_after_insert(mapper, connection, target):
    """Trigger after a new AudioGenerationJob is inserted"""
    target.on_create_trigger()
    
