from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from db.session import Base
import sqlalchemy

class PersistentData(Base):
    __tablename__ = "persistent_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    key = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship with User
    user = relationship("User", back_populates="persistent_data")

    # Composite unique constraint on user_id and key
    __table_args__ = (
        # This ensures each user can only have one entry per key
        sqlalchemy.UniqueConstraint('user_id', 'key', name='uix_user_key'),
    ) 