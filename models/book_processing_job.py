from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db.session import Base
from models.job_status import JobStatus
from datetime import datetime

class BookProcessingJob(Base):
    __tablename__ = "book_processing_job"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    result = Column(JSON, nullable=True)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=True)
    processed_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    data = Column(JSON, nullable=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="book_processing_jobs", lazy="select")
    book = relationship("Book", back_populates="processing_jobs", lazy="select")