from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from db.session import Base
from datetime import datetime

class DefaultVoice(Base):
    __tablename__ = "default_voice"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    s3_key = Column(String, nullable=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 