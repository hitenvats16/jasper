from sqlalchemy import Column, Integer, String, DateTime, JSON, func, ForeignKey, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from enum import Enum
from db.session import Base
from core.config import settings

class ProcessedVoiceChunksType(Enum):
    PARTIAL_AUDIO = "partial_audio"
    CHAPTER_AUDIO = "chapter_audio"

class ProcessedVoiceChunks(Base):
    __tablename__ = "processed_voice_chunks"

    id = Column(Integer, primary_key=True, index=True)
    s3_key = Column(String, nullable=False)  # S3 key for the chunk file
    index = Column(Integer, nullable=False)  # Used to sort the chunks
    chapter_id = Column(String, nullable=False)  # Unique chapter identifier
    data = Column(JSON, nullable=True)  # Chunk data
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=False)
    voice_processing_job_id = Column(Integer, ForeignKey("book_voice_processing_job.id"), nullable=False)
    type = Column(SQLAlchemyEnum(ProcessedVoiceChunksType), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="processed_voice_chunks", lazy="select")
    book = relationship("Book", back_populates="processed_voice_chunks", lazy="select")
    voice_processing_job = relationship("BookVoiceProcessingJob", back_populates="processed_chunks", lazy="select") 

    @property
    def s3_public_link(self):
        """Returns the public AWS S3 URL for this voice file."""
        return f"{settings.AWS_PUBLIC_URL}/{self.s3_key}"

