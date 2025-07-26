from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from db.session import Base
from core.config import settings
from datetime import datetime, timezone
from utils.s3 import get_presigned_url

class Voice(Base):
    __tablename__ = "voice"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    s3_key = Column(String, nullable=False)  # S3 key for file storage
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # User who generated
    voice_metadata = Column(JSON, nullable=True)  # JSON metadata storage
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="voices", lazy="select")

    @property
    def s3_public_link(self) -> str:
        """
        Returns a presigned URL for accessing the voice file.
        The URL is cached and automatically refreshed when needed.
        """
        if not self.s3_key:
            return None
        return get_presigned_url(self.s3_key)
