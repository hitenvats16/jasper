from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from models.payment import PlanType, PaymentStatus, RefundStatus

# Plan Schemas
class PaymentPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    currency: str = "USD"
    credits: int = Field(gt=0)
    plan_type: PlanType
    lemon_squeezy_variant_id: str
    lemon_squeezy_product_id: str
    is_active: bool = True

class PaymentPlanCreate(PaymentPlanBase):
    pass

class PaymentPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    credits: Optional[int] = Field(None, gt=0)
    plan_type: Optional[PlanType] = None
    lemon_squeezy_variant_id: Optional[str] = None
    lemon_squeezy_product_id: Optional[str] = None
    is_active: Optional[bool] = None

class PaymentPlanRead(PaymentPlanBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Removed subscription schemas - only one-time payments supported

# Payment Schemas
class PaymentBase(BaseModel):
    plan_id: int
    # Removed subscription_id - only one-time payments supported
    lemon_squeezy_order_id: str
    lemon_squeezy_order_number: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING
    credits_added: int = Field(ge=0)
    payment_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentCreate(PaymentBase):
    user_id: int

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    credits_added: Optional[int] = Field(None, ge=0)
    payment_metadata: Optional[Dict[str, Any]] = None

class PaymentRead(PaymentBase):
    id: int
    user_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    plan: Optional[PaymentPlanRead] = None
    # Removed subscription field - only one-time payments supported

    class Config:
        from_attributes = True

# Refund Schemas
class PaymentRefundBase(BaseModel):
    payment_id: int
    lemon_squeezy_refund_id: Optional[str] = None
    amount: float = Field(gt=0)
    currency: str = "USD"
    status: RefundStatus = RefundStatus.PENDING
    reason: Optional[str] = None
    credits_deducted: int = Field(ge=0)
    refund_metadata: Optional[Dict[str, Any]] = None

class PaymentRefundCreate(PaymentRefundBase):
    user_id: int

class PaymentRefundUpdate(BaseModel):
    status: Optional[RefundStatus] = None
    reason: Optional[str] = None
    credits_deducted: Optional[int] = Field(None, ge=0)
    refund_metadata: Optional[Dict[str, Any]] = None

class PaymentRefundRead(PaymentRefundBase):
    id: int
    user_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    payment: Optional[PaymentRead] = None

    class Config:
        from_attributes = True

# Checkout Session Schemas
class CreateCheckoutSessionRequest(BaseModel):
    plan_id: int
    success_url: str
    cancel_url: str
    custom_data: Optional[Dict[str, Any]] = None

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str

# Webhook Schemas
class WebhookContent(BaseModel):
    meta: Dict[str, Any]
    data: Dict[str, Any]

class LemonSqueezyWebhookData(BaseModel):
    id: str
    type: str
    attributes: Dict[str, Any]
    relationships: Optional[Dict[str, Any]] = None

class LemonSqueezyWebhookEvent(BaseModel):
    meta: Dict[str, Any]
    data: LemonSqueezyWebhookData

# User Payment Summary
class UserPaymentSummary(BaseModel):
    total_payments: int
    total_amount: float
    total_refunds: int
    refunded_amount: float
    current_credits: float

# Admin Schemas
class PaymentStats(BaseModel):
    total_revenue: float
    total_payments: int
    pending_payments: int
    failed_payments: int
    total_refunds: int
    refunded_amount: float 