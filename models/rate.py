from sqlalchemy import Column, Integer, String, Float, Boolean, JSON
from db.session import Base

class Rate(Base):
    __tablename__ = "rate"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    flags = Column(JSON, nullable=True)  # e.g. {"premium": true, "discount": false}
    rate = Column(Float, nullable=False)  # price per unit (e.g. per minute, per job, etc)
    currency = Column(String, default="USD", nullable=False)
    description = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False) 