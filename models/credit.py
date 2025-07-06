from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, func, Boolean
from sqlalchemy.orm import relationship
from db.session import Base
import enum

class TransactionType(str, enum.Enum):
    ADD = "add"
    DEDUCT = "deduct"
    USAGE = "usage"

class UserCredit(Base):
    __tablename__ = "user_credits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    is_deleted = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="credit")
    transactions = relationship("CreditTransaction", back_populates="user_credit", cascade="all, delete-orphan")

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_credit_id = Column(Integer, ForeignKey("user_credits.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_credit = relationship("UserCredit", back_populates="transactions") 