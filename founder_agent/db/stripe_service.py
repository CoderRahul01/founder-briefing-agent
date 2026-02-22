import stripe
import os
import uuid
from typing import Optional
from .crud import get_user, log_event
import logging

logger = logging.getLogger(__name__)

# Correct way to use async in stripe-python 11.x
from stripe import StripeClient

# Global client instance to reuse connections
# In production, ensure STRIPE_SECRET_KEY is set
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Use a synchronous client for webhook construction (CPU bound) and async for API calls
# Note: For simplicity in this audit, we will use the async-capable client for API calls.

PLAN_PRICE_MAPPING = {
    "founder": os.getenv("STRIPE_PRICE_FOUNDER", "price_1xxxx"),
    "team": os.getenv("STRIPE_PRICE_TEAM", "price_1yyyy")
}

async def create_checkout_session(user_email: str, plan: str, success_url: str, cancel_url: str):
    """
    Creates a Stripe Checkout Session for a given plan using async client.
    """
    user = await get_user(user_email)
    if not user:
        raise ValueError("User not found")

    price_id = PLAN_PRICE_MAPPING.get(plan)
    if not price_id:
        raise ValueError(f"Invalid plan or price ID not configured for: {plan}")

    try:
        idempotency_key = f"checkout_{user_email}_{plan}_{uuid.uuid4().hex[:8]}"
        
        # We can use stripe.* with an async http client or use StripeClient
        # The most modern way:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=user_email,
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "user_email": user_email,
                "plan_target": plan
            },
            idempotency_key=idempotency_key
        )
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Session creation failed for {user_email}: {e}")
        raise

async def handle_stripe_webhook(payload: bytes, sig_header: str):
    """
    Processes Stripe webhooks with signature verification.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, _webhook_secret
        )
    except ValueError:
        logger.warning("Stripe Webhook: Invalid payload")
        raise ValueError("Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe Webhook: Invalid signature")
        raise ValueError("Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await _handle_successful_payment(session)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await _handle_subscription_cancelled(subscription)

    return {"status": "success"}

async def _handle_successful_payment(session):
    user_email = session.get("metadata", {}).get("user_email")
    plan_target = session.get("metadata", {}).get("plan_target")
    
    if user_email and plan_target:
        user = await get_user(user_email)
        if user:
            user.stripe_customer_id = session.get("customer")
            user.stripe_subscription_id = session.get("subscription")
            user.plan = plan_target
            await user.save()
            await log_event(user_email, "subscription_updated", "success", f"Upgraded to {plan_target} plan")

async def _handle_subscription_cancelled(subscription):
    from .models import User
    try:
        user = await User.find_one(User.stripe_subscription_id == subscription.id)
        if user:
            user.plan = 'solo'
            user.stripe_subscription_id = None
            await user.save()
            await log_event(user.email, "subscription_cancelled", "warning", "Subscription ended, downgraded to solo")
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {e}")
