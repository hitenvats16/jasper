# LemonSqueezy Payment Integration

This document provides a comprehensive guide for the LemonSqueezy payment integration in the Jasper Voice Gateway application.

## Overview

The payment system integrates LemonSqueezy as the payment gateway, providing:
- **One-time purchases** for voice generation credits
- **Automatic credit allocation** when payments are successful
- **Refund management** with proportional credit deduction
- **Webhook processing** for real-time payment updates
- **Admin dashboard** for payment analytics and management

## Features

### 🛒 Payment Plans
- **Starter Pack**: $9.99 for 100 credits
- **Pro Pack**: $29.99 for 500 credits
- **Premium Pack**: $49.99 for 1000 credits
- **Enterprise Pack**: $99.99 for 2500 credits
- **Ultimate Pack**: $199.99 for 5000 credits

### 💳 Payment Processing
- Secure checkout sessions via LemonSqueezy
- Real-time payment status updates via webhooks
- Automatic credit allocation upon successful payment
- Support for multiple currencies (default: USD)

### 🔄 One-Time Purchases
- Simple credit-based system
- No recurring billing
- Pay-as-you-go model
- Immediate credit allocation

### 💰 Refund System
- Full and partial refunds
- Proportional credit deduction
- Refund reason tracking
- Refund status management

### 📊 Admin Features
- Payment analytics and statistics
- User payment history
- Refund processing
- Plan management

## Setup Instructions

### 1. Environment Variables

Add the following environment variables to your `.env` file:

```env
# LemonSqueezy Configuration
LEMON_SQUEEZY_API_KEY=your_api_key_here
LEMON_SQUEEZY_WEBHOOK_SECRET=your_webhook_secret_here
LEMON_SQUEEZY_STORE_ID=your_store_id_here
```

### 2. LemonSqueezy Store Setup

1. **Create a LemonSqueezy Store**:
   - Sign up at [lemonsqueezy.com](https://lemonsqueezy.com)
   - Create a new store for your application

2. **Create Products**:
   - Create products for each plan (one-time purchases and subscriptions)
   - Note down the `product_id` and `variant_id` for each plan

3. **Configure Webhooks**:
   - Go to Store Settings → Webhooks
   - Add webhook URL: `https://your-domain.com/api/v1/payments/webhook`
   - Select events: `order_created`, `order_updated`
   - Copy the webhook secret

4. **Get API Key**:
   - Go to Account Settings → API
   - Generate a new API key

### 3. Database Migration

Run the migration script to create payment tables:

```bash
python migrations/add_payment_tables.py
```

### 4. Update Plan Configuration

Update the sample plans in the migration script with your actual LemonSqueezy product and variant IDs:

```sql
UPDATE payment_plan 
SET lemon_squeezy_variant_id = 'your_variant_id',
    lemon_squeezy_product_id = 'your_product_id'
WHERE name = 'Starter Pack';
```

## API Endpoints

### Public Endpoints

#### Get Available Plans
```http
GET /api/v1/payments/plans
Authorization: Bearer <token>
```

#### Get Specific Plan
```http
GET /api/v1/payments/plans/{plan_id}
Authorization: Bearer <token>
```

#### Create Checkout Session
```http
POST /api/v1/payments/checkout
Authorization: Bearer <token>
Content-Type: application/json

{
  "plan_id": 1,
  "success_url": "https://your-app.com/success",
  "cancel_url": "https://your-app.com/cancel",
  "custom_data": {
    "source": "web"
  }
}
```

### User Endpoints

#### Get User Payment History
```http
GET /api/v1/payments/my-payments
Authorization: Bearer <token>
```

# Removed subscription endpoints - only one-time payments supported

#### Get Payment Summary
```http
GET /api/v1/payments/my-payment-summary
Authorization: Bearer <token>
```

#### Request Refund
```http
POST /api/v1/payments/refunds
Authorization: Bearer <token>
Content-Type: application/json

{
  "payment_id": 123,
  "amount": 9.99,
  "reason": "Customer requested refund"
}
```

#### Get Refund History
```http
GET /api/v1/payments/my-refunds
Authorization: Bearer <token>
```

### Admin Endpoints

#### Create Plan (Admin Only)
```http
POST /api/v1/payments/admin/plans
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Enterprise Pack",
  "description": "For enterprise customers",
  "price": 99.99,
  "currency": "USD",
  "credits": 5000,
  "plan_type": "one_time",
  "lemon_squeezy_variant_id": "12345",
  "lemon_squeezy_product_id": "prod_123"
}
```

#### Update Plan (Admin Only)
```http
PUT /api/v1/payments/admin/plans/{plan_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "price": 89.99,
  "credits": 6000
}
```

#### Get All Payments (Admin Only)
```http
GET /api/v1/payments/admin/payments?status=completed&skip=0&limit=50
Authorization: Bearer <admin_token>
```

#### Get Payment Statistics (Admin Only)
```http
GET /api/v1/payments/admin/stats
Authorization: Bearer <admin_token>
```

### Webhook Endpoint

#### LemonSqueezy Webhook
```http
POST /api/v1/payments/webhook
Content-Type: application/json
X-Signature: sha256=...

{
  "meta": {
    "event_name": "order_created"
  },
  "data": {
    "id": "order_id",
    "attributes": {
      "total": 999,
      "currency": "USD",
      "status": "pending",
      "custom_data": {
        "user_id": 123,
        "plan_id": 1
      }
    }
  }
}
```

## Usage Examples

### Frontend Integration

#### 1. Display Available Plans
```javascript
// Get available plans
const response = await fetch('/api/v1/payments/plans', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const plans = await response.json();

// Display plans to user
plans.forEach(plan => {
  console.log(`${plan.name}: $${plan.price} for ${plan.credits} credits`);
});
```

#### 2. Create Checkout Session
```javascript
// Create checkout session
const response = await fetch('/api/v1/payments/checkout', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    plan_id: 1,
    success_url: 'https://your-app.com/success',
    cancel_url: 'https://your-app.com/cancel'
  })
});

const { checkout_url } = await response.json();

// Redirect to checkout
window.location.href = checkout_url;
```

#### 3. Handle Payment Success
```javascript
// On success page, check payment status
const urlParams = new URLSearchParams(window.location.search);
const orderId = urlParams.get('order_id');

if (orderId) {
  // Payment was successful, credits should be added automatically
  // You can show a success message to the user
  showSuccessMessage('Payment successful! Credits have been added to your account.');
}
```

### Backend Integration

#### 1. Check User Credits
```python
from services.credit_service import CreditService

# Get user's current credit balance
balance = CreditService.get_balance(db, user_id)
print(f"User has {balance} credits")
```

#### 2. Process Refund
```python
from services.lemonsqueezy_service import LemonSqueezyService

# Create refund for a payment
refund = lemonsqueezy_service.create_refund(
    db=db,
    payment_id=123,
    amount=9.99,
    reason="Customer requested refund"
)
```

#### 3. Get Payment Analytics
```python
# Get payment statistics
stats = lemonsqueezy_service.get_user_payment_summary(db, user_id)
print(f"Total spent: ${stats['total_amount']}")
print(f"Total payments: {stats['total_payments']}")
```

## Webhook Processing

The system automatically processes LemonSqueezy webhooks for:

1. **Order Created**: Creates payment record
2. **Order Updated**: Updates payment status and adds credits

### Webhook Security

Webhooks are verified using HMAC-SHA256 signatures to ensure they come from LemonSqueezy.

## Error Handling

### Common Error Responses

```json
{
  "detail": "Plan not found or inactive"
}
```

```json
{
  "detail": "Payment must be completed to refund"
}
```

```json
{
  "detail": "Admin access required"
}
```

### Error Codes

- `400`: Bad Request (invalid data, plan not found, etc.)
- `401`: Unauthorized (invalid token)
- `403`: Forbidden (admin access required)
- `404`: Not Found (resource not found)
- `500`: Internal Server Error (webhook processing failed, etc.)

## Testing

### Test Mode

For testing, you can use LemonSqueezy's test mode:

1. Use test API keys
2. Create test products
3. Use test webhook endpoints
4. Test with test payment methods

### Sample Test Data

```json
{
  "plan_id": 1,
  "success_url": "http://localhost:3000/success",
  "cancel_url": "http://localhost:3000/cancel"
}
```

## Security Considerations

1. **Webhook Verification**: Always verify webhook signatures
2. **API Key Security**: Keep API keys secure and rotate regularly
3. **HTTPS**: Use HTTPS for all webhook endpoints
4. **Input Validation**: Validate all input data
5. **Rate Limiting**: Implement rate limiting on payment endpoints

## Monitoring

### Key Metrics to Monitor

1. **Payment Success Rate**: Track successful vs failed payments
2. **Webhook Processing**: Monitor webhook processing success
3. **Credit Allocation**: Ensure credits are added correctly
4. **Refund Rate**: Track refund requests and processing
5. **Plan Performance**: Monitor which plans are most popular

### Logging

The system logs important events:
- Payment creation and updates
- Credit allocation
- Refund processing
- Webhook events
- Error conditions

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**:
   - Check webhook URL is accessible
   - Verify webhook secret is correct
   - Check firewall/network settings

2. **Credits Not Added**:
   - Verify payment status is "completed"
   - Check webhook processing logs
   - Verify plan credits configuration

3. **Checkout Session Creation Fails**:
   - Verify API key is correct
   - Check plan is active
   - Verify variant ID exists

4. **Refund Processing Issues**:
   - Verify payment is completed
   - Check user has sufficient credits
   - Verify refund amount doesn't exceed payment amount

### Debug Mode

Enable debug logging by setting log level to DEBUG:

```python
import logging
logging.getLogger('services.lemonsqueezy_service').setLevel(logging.DEBUG)
```

## Support

For issues with the payment integration:

1. Check the logs for error messages
2. Verify LemonSqueezy configuration
3. Test webhook endpoints
4. Contact support with detailed error information

## Future Enhancements

Potential future improvements:

1. **Multiple Payment Gateways**: Support for Stripe, PayPal, etc.
2. **Advanced Analytics**: Detailed payment analytics and reporting
3. **Automated Refunds**: Automatic refund processing based on rules
4. **Bulk Purchase Discounts**: Volume discounts for larger credit purchases
5. **Usage-Based Billing**: Pay-per-use instead of credit-based
6. **Multi-Currency Support**: Better support for multiple currencies
7. **Tax Calculation**: Automatic tax calculation and collection 