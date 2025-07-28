from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from db.session import Base
import logging

logger = logging.getLogger(__name__)

class AudioChunk(Base):
    __tablename__ = "audio_chunk"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, index=True)
    index = Column(Integer, nullable=False)
    audio_generation_job_id = Column(Integer, ForeignKey("audio_generation_job.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    s3_key = Column(String, nullable=False)
    text = Column(String, nullable=False)
    chunk_meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    audio_generation_job = relationship("AudioGenerationJob", back_populates="audio_chunks", lazy="select")
    user = relationship("User", back_populates="audio_chunks", lazy="select") 