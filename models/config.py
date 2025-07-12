from sqlalchemy import Column, Integer, String, DateTime, JSON, func, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from db.session import Base

class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True)
    tts_model = Column(String, nullable=True)  # TTS model configuration
    silence_strategy = Column(String, nullable=True)  # Silence strategy configuration
    silence_data = Column(JSON, nullable=True)  # Silence strategy specific data
    tts_model_data = Column(JSON, nullable=True)  # TTS model specific configuration data
    sample_rate = Column(Integer, nullable=True, default=24000)  # Audio sample rate (e.g., 22050, 44100)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="config", lazy="joined")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'is_deleted', name='uq_user_config'),
    ) 