import httpx
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from core.config import settings
from models.payment import (
    PaymentPlan, Payment, PaymentRefund,
    PaymentStatus, RefundStatus, PlanType
)
from models.user import User
from services.credit_service import CreditService
from schemas.payment import (
    CreateCheckoutSessionRequest, CheckoutSessionResponse,
    LemonSqueezyWebhookEvent
)

logger = logging.getLogger(__name__)

class LemonSqueezyService:
    def __init__(self):
        self.api_key = settings.LEMON_SQUEEZY_API_KEY
        self.webhook_secret = settings.LEMON_SQUEEZY_WEBHOOK_SECRET
        self.store_id = settings.LEMON_SQUEEZY_STORE_ID
        self.base_url = "https://api.lemonsqueezy.com/v1"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for LemonSqueezy API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def create_checkout_session(
        self, 
        db: Session, 
        user: User, 
        request: CreateCheckoutSessionRequest
    ) -> CheckoutSessionResponse:
        """Create a checkout session for a plan"""
        try:
            # Validate required settings
            if not self.api_key:
                raise ValueError("LEMON_SQUEEZY_API_KEY is not configured")
            if not self.store_id:
                raise ValueError("LEMON_SQUEEZY_STORE_ID is not configured")
            
            # Get the plan
            plan = db.query(PaymentPlan).filter(
                PaymentPlan.id == request.plan_id,
                PaymentPlan.is_active == True,
                PaymentPlan.is_deleted == False
            ).first()
            
            if not plan:
                raise ValueError(f"Plan with ID {request.plan_id} not found or inactive")
            
            if not plan.lemon_squeezy_variant_id:
                raise ValueError(f"Plan {plan.name} has no LemonSqueezy variant ID configured")
            
            logger.info(f"Creating checkout session for plan: {plan.name} (ID: {plan.id}, Variant: {plan.lemon_squeezy_variant_id})")
            
            # Prepare checkout data
            checkout_data = {
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "custom_price": None,
                        "product_options": {
                            "enabled_variants": [int(plan.lemon_squeezy_variant_id)],
                            "redirect_url": request.success_url,
                            "receipt_button_text": "Continue to Jasper",
                            "receipt_link_url": request.success_url
                        },
                        "checkout_options": {
                            "embed": False,
                            "media": False,
                            "logo": True
                        },
                        "checkout_data": {
                            "email": user.email,
                            "custom": {
                                "user_id": str(user.id),
                                "plan_id": str(plan.id),
                                "plan_type": str(plan.plan_type.value),
                                "credits": str(plan.credits),
                                **{k: str(v) for k, v in (request.custom_data or {}).items()}
                            }
                        }
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": str(self.store_id)
                            }
                        },
                        "variant": {
                            "data": {
                                "type": "variants",
                                "id": str(plan.lemon_squeezy_variant_id)
                            }
                        }
                    }
                }
            }

            # Use correct headers for LemonSqueezy API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json"
            }

            logger.info(f"Checkout data prepared: {json.dumps(checkout_data, indent=2)}")

            # Create checkout session
            async with httpx.AsyncClient(timeout=10.0) as client:  # Reduced timeout from 30 to 10 seconds
                response = await client.post(
                    f"{self.base_url}/checkouts",
                    headers=headers,
                    json=checkout_data
                )
                
                logger.info(f"LemonSqueezy API response status: {response.status_code}")
                
                if response.status_code != 201:  # LemonSqueezy returns 201 for created checkout
                    error_detail = f"LemonSqueezy API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "errors" in error_data:
                            error_detail += f" - {error_data['errors']}"
                        elif "message" in error_data:
                            error_detail += f" - {error_data['message']}"
                    except:
                        error_detail += f" - {response.text}"
                    
                    logger.error(f"Checkout session creation failed: {error_detail}")
                    raise ValueError(error_detail)
                
                data = response.json()
                logger.info(f"Checkout session created successfully: {data}")
                
                checkout_url = data["data"]["attributes"]["url"]
                session_id = data["data"]["id"]
                
                return CheckoutSessionResponse(
                    checkout_url=checkout_url,
                    session_id=session_id
                )
                
        except ValueError as e:
            # Re-raise ValueError as-is (these are validation errors)
            logger.error(f"Validation error in checkout session creation: {str(e)}")
            raise
        except httpx.TimeoutException:
            error_msg = "LemonSqueezy API request timed out"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Network error connecting to LemonSqueezy API: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating checkout session: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True
        
        if not signature:
            logger.warning("No signature provided, skipping signature verification")
            return True
            
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    def process_webhook(self, db: Session, event_data: Dict[str, Any]) -> bool:
        """Process LemonSqueezy webhook events"""
        try:
            # Handle both new and old webhook structures
            event_type = None
            data = None
            
            # Check for event_name in meta (new structure)
            if "meta" in event_data and "event_name" in event_data["meta"]:
                event_type = event_data["meta"]["event_name"]
                data = event_data.get("data", {})
            # Fallback to old structure
            elif "event_name" in event_data:
                event_type = event_data["event_name"]
                data = event_data.get("data", {})
            
            if not event_type:
                logger.error("No event_name found in webhook data")
                logger.error(f"Webhook data keys: {list(event_data.keys())}")
                return False
            
            logger.info(f"Processing webhook event: {event_type}")
            logger.info(f"Webhook data structure: {list(event_data.keys())}")
            print(event_data)
            if event_type == "order_created":
                return self._handle_order_created(db, event_data)
            elif event_type == "order_updated":
                return self._handle_order_updated(db, event_data)
            # Removed subscription webhook handlers - only one-time payments supported
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to process webhook: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _handle_order_created(self, db: Session, event_data: Dict[str, Any]) -> bool:
        """Handle order_created webhook"""
        try:
            # Extract data from the new webhook structure
            data = event_data.get("data", {})
            meta = event_data.get("meta", {})
            attributes = data.get("attributes", {})
            
            # Get custom_data from meta (new structure)
            custom_data = meta.get("custom_data", {})
            
            if not custom_data:
                logger.error("No custom_data found in webhook meta")
                return False
            
            # Extract and validate user_id and plan_id with proper type conversion
            user_id_raw = custom_data.get("user_id")
            plan_id_raw = custom_data.get("plan_id")
            
            if user_id_raw is None or plan_id_raw is None:
                logger.error(f"Missing user_id or plan_id in custom_data: user_id={user_id_raw}, plan_id={plan_id_raw}")
                return False
            
            # Convert to integers, handling both string and int inputs
            try:
                user_id = int(user_id_raw) if user_id_raw is not None else None
                plan_id = int(plan_id_raw) if plan_id_raw is not None else None
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid user_id or plan_id format: user_id={user_id_raw}, plan_id={plan_id_raw}, error={str(e)}")
                return False
            
            if user_id is None or plan_id is None:
                logger.error(f"Failed to convert user_id or plan_id to integer: user_id={user_id}, plan_id={plan_id}")
                return False
            
            logger.info(f"Processing order_created webhook: user_id={user_id}, plan_id={plan_id}")
            
            # Get the plan
            plan = db.query(PaymentPlan).filter(
                PaymentPlan.id == plan_id,
                PaymentPlan.is_deleted == False
            ).first()
            
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return False
            
            # Convert amount from cents to dollars, handling None values
            total_cents = attributes.get("total")
            if total_cents is None:
                logger.error("No total amount found in webhook attributes")
                return False
            
            try:
                amount = float(total_cents) / 100  # Convert from cents
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid total amount format: {total_cents}, error={str(e)}")
                return False
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                plan_id=plan_id,
                lemon_squeezy_order_id=data["id"],
                lemon_squeezy_order_number=attributes.get("order_number"),
                amount=amount,
                currency=attributes.get("currency", "USD"),
                status=PaymentStatus.PENDING,
                credits_added=plan.credits,
                payment_metadata=event_data
            )
            
            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Add credits to user
            CreditService.add_credit(
                db, 
                user_id, 
                float(plan.credits),
                f"Payment for {plan.name} - Order {data['id']}"
            )
            
            logger.info(f"Created payment record for order {data['id']}: payment_id={payment.id}, amount=${amount}, credits={plan.credits}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle order_created: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _handle_order_updated(self, db: Session, event_data: Dict[str, Any]) -> bool:
        """Handle order_updated webhook"""
        try:
            # Extract data from the new webhook structure
            data = event_data.get("data", {})
            attributes = data.get("attributes", {})
            
            order_id = data["id"]
            status = attributes.get("status")
            
            logger.info(f"Processing order_updated webhook for order {order_id} with status: {status}")
            
            # Find the payment
            payment = db.query(Payment).filter(
                Payment.lemon_squeezy_order_id == order_id,
                Payment.is_deleted == False
            ).first()
            
            if not payment:
                logger.error(f"Payment not found for order {order_id}")
                return False
            
            # Update payment status
            if status == "paid":
                payment.status = PaymentStatus.COMPLETED
                # Add credits to user
                try:
                    CreditService.add_credit(
                        db, 
                        payment.user_id, 
                        float(payment.credits_added),
                        f"Payment for {payment.plan.name} - Order {order_id}"
                    )
                    logger.info(f"Payment completed and credits added for order {order_id}. Credits added: {payment.credits_added}")
                except Exception as e:
                    logger.error(f"Failed to add credits for order {order_id}: {str(e)}")
                    # Don't fail the webhook processing if credit addition fails
            elif status == "failed":
                payment.status = PaymentStatus.FAILED
                logger.info(f"Payment failed for order {order_id}")
            elif status == "pending":
                payment.status = PaymentStatus.PENDING
                logger.info(f"Payment status updated to pending for order {order_id}")
            else:
                logger.info(f"Payment status updated to {status} for order {order_id}")
            
            payment.payment_metadata = event_data
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle order_updated: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    # Removed subscription handler methods - only one-time payments supported
    
    def create_refund(self, db: Session, payment_id: int, amount: float, reason: str) -> PaymentRefund:
        """Create a refund for a payment"""
        try:
            # Get the payment
            payment = db.query(Payment).filter(
                Payment.id == payment_id,
                Payment.is_deleted == False
            ).first()
            
            if not payment:
                raise ValueError("Payment not found")
            
            if payment.status != PaymentStatus.COMPLETED:
                raise ValueError("Payment must be completed to refund")
            
            # Calculate credits to deduct (proportional to refund amount)
            refund_ratio = amount / payment.amount
            credits_to_deduct = int(payment.credits_added * refund_ratio)
            
            # Create refund record
            refund = PaymentRefund(
                payment_id=payment_id,
                user_id=payment.user_id,
                amount=amount,
                currency=payment.currency,
                status=RefundStatus.PENDING,
                reason=reason,
                credits_deducted=credits_to_deduct
            )
            
            db.add(refund)
            db.commit()
            db.refresh(refund)
            
            # Deduct credits from user
            CreditService.deduct_credit(
                db,
                payment.user_id,
                float(credits_to_deduct),
                f"Refund for payment {payment_id} - {reason}"
            )
            
            # Update payment status
            payment.status = PaymentStatus.REFUNDED
            db.commit()
            
            logger.info(f"Created refund for payment {payment_id}")
            return refund
            
        except Exception as e:
            logger.error(f"Failed to create refund: {str(e)}")
            raise
    
    def get_user_payment_summary(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get payment summary for a user"""
        try:
            # Get total payments
            total_payments = db.query(Payment).filter(
                Payment.user_id == user_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.is_deleted == False
            ).count()
            
            # Get total amount
            total_amount = db.query(Payment).filter(
                Payment.user_id == user_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.is_deleted == False
            ).with_entities(func.sum(Payment.amount)).scalar() or 0.0
            
            # Removed active subscriptions count - only one-time payments supported
            
            # Get total refunds
            total_refunds = db.query(PaymentRefund).filter(
                PaymentRefund.user_id == user_id,
                PaymentRefund.status == RefundStatus.COMPLETED,
                PaymentRefund.is_deleted == False
            ).count()
            
            # Get refunded amount
            refunded_amount = db.query(PaymentRefund).filter(
                PaymentRefund.user_id == user_id,
                PaymentRefund.status == RefundStatus.COMPLETED,
                PaymentRefund.is_deleted == False
            ).with_entities(func.sum(PaymentRefund.amount)).scalar() or 0.0
            
            # Get current credits
            current_credits = CreditService.get_balance(db, user_id)
            
            return {
                "total_payments": total_payments,
                "total_amount": total_amount,
                "total_refunds": total_refunds,
                "refunded_amount": refunded_amount,
                "current_credits": current_credits
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment summary: {str(e)}")
            raise

    async def fetch_products(self) -> List[Dict[str, Any]]:
        """Fetch all products from LemonSqueezy API"""
        try:
            products = []
            page = 1
            
            while True:
                async with httpx.AsyncClient(timeout=10.0) as client:  # Reduced timeout from 30 to 10 seconds
                    response = await client.get(
                        f"{self.base_url}/products",
                        headers=self._get_headers(),
                        params={
                            "page[number]": page,
                            "page[size]": 100,
                            "sort": "name"
                        }
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    products_data = data.get("data", [])
                    
                    if not products_data:
                        break
                    
                    products.extend(products_data)
                    
                    # Check if there are more pages
                    meta = data.get("meta", {})
                    page_info = meta.get("page", {})
                    current_page = page_info.get("currentPage", 1)
                    last_page = page_info.get("lastPage", 1)
                    
                    if current_page >= last_page:
                        break
                    
                    page += 1
            
            logger.info(f"Fetched {len(products)} products from LemonSqueezy")
            return products
            
        except Exception as e:
            logger.error(f"Failed to fetch products from LemonSqueezy: {str(e)}")
            raise

    async def sync_products_to_plans(self, db: Session) -> Dict[str, Any]:
        """Sync LemonSqueezy products to payment plans table"""
        try:
            logger.info("Starting product sync from LemonSqueezy...")
            
            # Fetch products from LemonSqueezy
            products = await self.fetch_products()
            
            if not products:
                logger.warning("No products found in LemonSqueezy")
                return {"synced": 0, "updated": 0, "created": 0, "errors": 0}
            
            synced_count = 0
            updated_count = 0
            created_count = 0
            error_count = 0
            
            for product in products:
                try:
                    product_id = product["id"]
                    attributes = product["attributes"]
                    
                    # Skip if product is not published
                    if attributes.get("status") != "published":
                        logger.info(f"Skipping unpublished product: {attributes.get('name')}")
                        continue
                    
                    # Get product variants to determine credits
                    variants = await self._fetch_product_variants(product_id)
                    
                    for variant in variants:
                        variant_id = variant["id"]
                        variant_attrs = variant["attributes"]
                        
                        # Determine credits based on product name and price
                        credits = self._determine_credits_for_product(
                            attributes.get("name", ""),
                            variant_attrs.get("price", 0)
                        )
                        
                        # Check if plan already exists
                        existing_plan = db.query(PaymentPlan).filter(
                            PaymentPlan.lemon_squeezy_variant_id == variant_id,
                            PaymentPlan.is_deleted == False
                        ).first()
                        
                        plan_data = {
                            "name": attributes.get("name", ""),
                            "description": attributes.get("description", ""),
                            "price": float(variant_attrs.get("price", 0)) / 100,  # Convert from cents
                            "currency": "USD",
                            "credits": credits,
                            "plan_type": PlanType.ONE_TIME,
                            "lemon_squeezy_variant_id": variant_id,
                            "lemon_squeezy_product_id": product_id,
                            "is_active": True
                        }
                        
                        if existing_plan:
                            # Update existing plan
                            for key, value in plan_data.items():
                                setattr(existing_plan, key, value)
                            updated_count += 1
                            logger.info(f"Updated plan: {plan_data['name']} (variant: {variant_id})")
                        else:
                            # Create new plan
                            new_plan = PaymentPlan(**plan_data)
                            db.add(new_plan)
                            created_count += 1
                            logger.info(f"Created plan: {plan_data['name']} (variant: {variant_id})")
                        
                        synced_count += 1
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error syncing product {product.get('id', 'unknown')}: {str(e)}")
                    continue
            
            # Commit all changes
            db.commit()
            
            result = {
                "synced": synced_count,
                "updated": updated_count,
                "created": created_count,
                "errors": error_count
            }
            
            logger.info(f"Product sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync products: {str(e)}")
            db.rollback()
            raise

    async def _fetch_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """Fetch variants for a specific product"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:  # Reduced timeout from 30 to 10 seconds
                response = await client.get(
                    f"{self.base_url}/products/{product_id}/variants",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("data", [])
                
        except Exception as e:
            logger.error(f"Failed to fetch variants for product {product_id}: {str(e)}")
            return []

    def _determine_credits_for_product(self, product_name: str, price_cents: int) -> int:
        """Determine credits based on product name and price"""
        price_dollars = price_cents / 100
        
        # Default credit calculation: $1 = 1 credit
        base_credits = int(price_dollars)
        
        # Adjust based on product name patterns
        product_name_lower = product_name.lower()
        
        if "short" in product_name_lower or "prelaunch" in product_name_lower:
            # Short book or prelaunch products get more credits per dollar
            return max(base_credits, 50)  # Minimum 50 credits
        elif "full" in product_name_lower:
            # Full book products get standard credits
            return max(base_credits, 100)  # Minimum 100 credits
        elif "big" in product_name_lower:
            # Big book products get more credits
            return max(base_credits, 200)  # Minimum 200 credits
        elif "publisher" in product_name_lower:
            # Publisher plans get premium credits
            return max(base_credits, 500)  # Minimum 500 credits
        elif "enterprise" in product_name_lower:
            # Enterprise plans get maximum credits
            return max(base_credits, 1000)  # Minimum 1000 credits
        else:
            # Default case
            return max(base_credits, 25)  # Minimum 25 credits 