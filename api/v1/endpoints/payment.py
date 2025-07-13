from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from models.user import User
from models.payment import (
    PaymentPlan, Payment, PaymentRefund,
    PaymentStatus, RefundStatus
)
from schemas.payment import (
    PaymentPlanCreate, PaymentPlanUpdate, PaymentPlanRead,
    PaymentRead, PaymentRefundRead,
    CreateCheckoutSessionRequest, CheckoutSessionResponse,
    UserPaymentSummary, PaymentStats
)
from services.lemonsqueezy_service import LemonSqueezyService
from db.session import get_db
from core.dependencies import get_current_user, get_current_admin_user
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])
lemonsqueezy_service = LemonSqueezyService()

# Plan Management Endpoints
@router.get("/plans", response_model=List[PaymentPlanRead], summary="Get all available payment plans")
def get_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active payment plans"""
    plans = db.query(PaymentPlan).filter(
        PaymentPlan.is_active == True,
        PaymentPlan.is_deleted == False
    ).all()
    return plans

@router.get("/plans/{plan_id}", response_model=PaymentPlanRead, summary="Get a specific payment plan")
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific payment plan by ID"""
    plan = db.query(PaymentPlan).filter(
        PaymentPlan.id == plan_id,
        PaymentPlan.is_active == True,
        PaymentPlan.is_deleted == False
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan

# Admin Plan Management
@router.post("/admin/plans", response_model=PaymentPlanRead, summary="Create a new payment plan (Admin only)")
def create_plan(
    plan_data: PaymentPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new payment plan (Admin only)"""
    plan = PaymentPlan(**plan_data.dict())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.put("/admin/plans/{plan_id}", response_model=PaymentPlanRead, summary="Update a payment plan (Admin only)")
def update_plan(
    plan_id: int,
    plan_data: PaymentPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a payment plan (Admin only)"""
    plan = db.query(PaymentPlan).filter(
        PaymentPlan.id == plan_id,
        PaymentPlan.is_deleted == False
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = plan_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/admin/plans/{plan_id}", summary="Delete a payment plan (Admin only)")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a payment plan (Admin only)"""
    plan = db.query(PaymentPlan).filter(
        PaymentPlan.id == plan_id,
        PaymentPlan.is_deleted == False
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.is_deleted = True
    db.commit()
    return {"message": "Plan deleted successfully"}

# Checkout Session Endpoints
@router.post("/checkout", response_model=CheckoutSessionResponse, summary="Create a checkout session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a checkout session for a plan"""
    try:
        return await lemonsqueezy_service.create_checkout_session(db, current_user, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

# Webhook Endpoint
@router.post("/webhook", summary="LemonSqueezy webhook endpoint")
async def webhook_handler(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle LemonSqueezy webhook events"""
    try:
        # Get the raw body
        body = await request.body()
        
        # Verify webhook signature
        signature = request.headers.get("x-signature")
        if not lemonsqueezy_service.verify_webhook_signature(body, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Parse the webhook data
        event_data = await request.json()
        
        # Process the webhook
        success = lemonsqueezy_service.process_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# User Payment Management
@router.get("/my-payments", response_model=List[PaymentRead], summary="Get user's payment history")
def get_user_payments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payment history for the current user"""
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id,
        Payment.is_deleted == False
    ).offset(skip).limit(limit).all()
    
    return payments

# Removed subscription endpoint - only one-time payments supported

@router.get("/my-payment-summary", response_model=UserPaymentSummary, summary="Get user's payment summary")
def get_user_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payment summary for the current user"""
    try:
        summary = lemonsqueezy_service.get_user_payment_summary(db, current_user.id)
        return UserPaymentSummary(**summary)
    except Exception as e:
        logger.error(f"Failed to get payment summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get payment summary")

# Refund Management
@router.post("/refunds", response_model=PaymentRefundRead, summary="Request a refund")
def create_refund(
    payment_id: int,
    amount: float,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request a refund for a payment"""
    try:
        # Verify the payment belongs to the user
        payment = db.query(Payment).filter(
            Payment.id == payment_id,
            Payment.user_id == current_user.id,
            Payment.is_deleted == False
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        if payment.status != PaymentStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Payment must be completed to refund")
        
        if amount > payment.amount:
            raise HTTPException(status_code=400, detail="Refund amount cannot exceed payment amount")
        
        refund = lemonsqueezy_service.create_refund(db, payment_id, amount, reason)
        return refund
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create refund: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create refund")

@router.get("/my-refunds", response_model=List[PaymentRefundRead], summary="Get user's refund history")
def get_user_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get refund history for the current user"""
    refunds = db.query(PaymentRefund).filter(
        PaymentRefund.user_id == current_user.id,
        PaymentRefund.is_deleted == False
    ).all()
    
    return refunds

# Admin Payment Management
@router.get("/admin/payments", response_model=List[PaymentRead], summary="Get all payments (Admin only)")
def get_all_payments(
    skip: int = 0,
    limit: int = 100,
    status: Optional[PaymentStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all payments (Admin only)"""
    query = db.query(Payment).filter(Payment.is_deleted == False)
    
    if status:
        query = query.filter(Payment.status == status)
    
    payments = query.offset(skip).limit(limit).all()
    return payments

# Removed subscription admin endpoint - only one-time payments supported

@router.get("/admin/refunds", response_model=List[PaymentRefundRead], summary="Get all refunds (Admin only)")
def get_all_refunds(
    skip: int = 0,
    limit: int = 100,
    status: Optional[RefundStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all refunds (Admin only)"""
    query = db.query(PaymentRefund).filter(PaymentRefund.is_deleted == False)
    
    if status:
        query = query.filter(PaymentRefund.status == status)
    
    refunds = query.offset(skip).limit(limit).all()
    return refunds

@router.get("/admin/stats", response_model=PaymentStats, summary="Get payment statistics (Admin only)")
def get_payment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get payment statistics (Admin only)"""
    try:
        # Total revenue
        total_revenue = db.query(Payment).filter(
            Payment.status == PaymentStatus.COMPLETED,
            Payment.is_deleted == False
        ).with_entities(func.sum(Payment.amount)).scalar() or 0.0
        
        # Total payments
        total_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.COMPLETED,
            Payment.is_deleted == False
        ).count()
        
        # Removed active subscriptions count - only one-time payments supported
        
        # Pending payments
        pending_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING,
            Payment.is_deleted == False
        ).count()
        
        # Failed payments
        failed_payments = db.query(Payment).filter(
            Payment.status == PaymentStatus.FAILED,
            Payment.is_deleted == False
        ).count()
        
        # Total refunds
        total_refunds = db.query(PaymentRefund).filter(
            PaymentRefund.status == RefundStatus.COMPLETED,
            PaymentRefund.is_deleted == False
        ).count()
        
        # Refunded amount
        refunded_amount = db.query(PaymentRefund).filter(
            PaymentRefund.status == RefundStatus.COMPLETED,
            PaymentRefund.is_deleted == False
        ).with_entities(func.sum(PaymentRefund.amount)).scalar() or 0.0
        
        return PaymentStats(
            total_revenue=total_revenue,
            total_payments=total_payments,
            pending_payments=pending_payments,
            failed_payments=failed_payments,
            total_refunds=total_refunds,
            refunded_amount=refunded_amount
        )
        
    except Exception as e:
        logger.error(f"Failed to get payment stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get payment statistics")

# Product Sync Endpoint
@router.post("/admin/sync-products", summary="Sync products from LemonSqueezy (Admin only)")
async def sync_products_from_lemonsqueezy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Sync products from LemonSqueezy to payment plans table (Admin only)"""
    try:
        sync_result = await lemonsqueezy_service.sync_products_to_plans(db)
        return {
            "message": "Product sync completed successfully",
            "result": sync_result
        }
    except Exception as e:
        logger.error(f"Failed to sync products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync products: {str(e)}") 