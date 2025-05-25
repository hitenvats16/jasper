from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, func
from db.session import Base
import enum

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VoiceProcessingJob(Base):
    __tablename__ = "voice_processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    s3_link = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 