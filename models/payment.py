from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, func, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from db.session import Base
import enum
from datetime import datetime

class PlanType(str, enum.Enum):
    ONE_TIME = "one_time"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentPlan(Base):
    __tablename__ = "payment_plan"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    credits = Column(Integer, nullable=False)  # Credits included in this plan
    plan_type = Column(Enum(PlanType), nullable=False)
    lemon_squeezy_variant_id = Column(String, nullable=False, unique=True)  # LemonSqueezy variant ID
    lemon_squeezy_product_id = Column(String, nullable=False)  # LemonSqueezy product ID
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    payments = relationship("Payment", back_populates="plan")

class Payment(Base):
    __tablename__ = "payment"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("payment_plan.id"), nullable=False)
    # Removed subscription_id - only one-time payments supported
    lemon_squeezy_order_id = Column(String, nullable=False, unique=True)
    lemon_squeezy_order_number = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    credits_added = Column(Integer, nullable=False)  # Credits added for this payment
    payment_metadata = Column(JSON, nullable=True)  # Store additional LemonSqueezy data
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="payments")
    plan = relationship("PaymentPlan", back_populates="payments")
    # Removed subscription relationship - only one-time payments supported
    refunds = relationship("PaymentRefund", back_populates="payment")

class PaymentRefund(Base):
    __tablename__ = "payment_refund"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payment.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    lemon_squeezy_refund_id = Column(String, nullable=True)  # If refunded through LemonSqueezy
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(Enum(RefundStatus), default=RefundStatus.PENDING)
    reason = Column(Text, nullable=True)
    credits_deducted = Column(Integer, nullable=False)  # Credits deducted for this refund
    refund_metadata = Column(JSON, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    user = relationship("User", back_populates="refunds") 