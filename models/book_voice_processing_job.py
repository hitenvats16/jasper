from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db.session import Base
from models.voice_job import JobStatus

class BookVoiceProcessingJob(Base):
    __tablename__ = "book_voice_processing_job"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    data = Column(JSON, nullable=True)  # Data to process
    result = Column(JSON, nullable=True)  # Info about result
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="book_voice_processing_jobs", lazy="joined")
    book = relationship("Book", back_populates="voice_processing_jobs", lazy="joined")
    processed_chunks = relationship("ProcessedVoiceChunks", back_populates="voice_processing_job", cascade="all, delete-orphan", lazy="joined") 