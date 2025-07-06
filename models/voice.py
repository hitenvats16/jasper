from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from db.session import Base
from datetime import datetime
from core.config import settings

class Voice(Base):
    __tablename__ = "voice"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    voice_metadata = Column(JSON, nullable=True)
    s3_key = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    is_default = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="voices")
    processing_jobs = relationship("VoiceProcessingJob", back_populates="voice", cascade="all, delete-orphan")

    @property
    def s3_public_link(self):
        """Returns the public AWS S3 URL for this voice file."""
        return f"{settings.AWS_PUBLIC_URL}/{self.s3_key}"
