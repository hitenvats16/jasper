from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from db.session import Base
from models.job_status import JobStatus
from utils.s3 import get_presigned_url

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

    # Relationships
    user = relationship("User", back_populates="audio_generation_jobs", lazy="select")
    project = relationship("Project", back_populates="audio_generation_jobs", lazy="select")
    voice = relationship("Voice", back_populates="audio_generation_jobs", lazy="select") 

    @property
    def s3_url(self):
        return get_presigned_url(self.input_data_s3_key)