from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func, JSON  
from sqlalchemy.orm import relationship
from db.session import Base
from utils.s3 import get_presigned_url
import enum


class AudiobookType(enum.Enum):
    FULL_AUDIO = "full_audio"
    CHAPTERWISE_AUDIO = "chapterwise_audio"


class AudiobookGeneration(Base):
    __tablename__ = "audiobook_generation"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    audio_generation_job_id = Column(Integer, ForeignKey("audio_generation_job.id"), nullable=False)
    key = Column(String, nullable=False)
    index = Column(Integer, nullable=True)  # Can be null
    type = Column(Enum(AudiobookType), nullable=False)
    s3_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    data = Column(JSON, nullable=True, default={})

    # Relationships
    user = relationship("User", back_populates="audiobook_generations", lazy="select")
    project = relationship("Project", back_populates="audiobook_generations", lazy="select")
    audio_generation_job = relationship("AudioGenerationJob", back_populates="audiobook_generations", lazy="select")

    @property
    def s3_url(self):
        """Virtual property that returns a presigned URL for the s3_key"""
        return get_presigned_url(self.s3_key) 