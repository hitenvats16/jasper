from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from db.session import Base
from core.config import settings

class Rate(Base):
    __tablename__ = "rate"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    values = Column(Float, nullable=False, default=settings.DEFAULT_PER_TOKEN_RATE)
    is_deleted = Column(Boolean, default=False)
    
    # Relationship with User
    user = relationship("User", back_populates="rate") 