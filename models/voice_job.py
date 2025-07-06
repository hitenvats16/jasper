from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db.session import Base
import enum

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VoiceProcessingJob(Base):
    __tablename__ = "voice_processing_job"

    id = Column(Integer, primary_key=True, index=True)
    s3_key = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add foreign keys
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    voice_id = Column(Integer, ForeignKey("voice.id"), nullable=True)  # Optional since not all jobs are for voice creation
    
    # Add relationships with string references to avoid circular imports
    user = relationship("User", back_populates="voice_jobs", lazy="joined", foreign_keys=[user_id])
    voice = relationship("Voice", back_populates="processing_jobs", lazy="joined", foreign_keys=[voice_id]) 