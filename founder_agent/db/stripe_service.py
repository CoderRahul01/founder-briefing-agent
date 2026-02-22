import stripe
import os
from typing import Optional
from .crud import get_user, log_event

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Plan to Price ID mapping (These should be in .env in production)
PLAN_PRICE_MAPPING = {
    "founder": os.getenv("STRIPE_PRICE_FOUNDER", "price_1xxxx"), # Replace with actual price ID from user's dashboard
    "team": os.getenv("STRIPE_PRICE_TEAM", "price_1yyyy")
}

async def create_checkout_session(user_email: str, plan: str, success_url: str, cancel_url: str):
    """
    Creates a Stripe Checkout Session for a given plan.
    """
    user = await get_user(user_email)
    if not user:
        raise ValueError("User not found")

    price_id = PLAN_PRICE_MAPPING.get(plan)
    if not price_id:
        raise ValueError(f"Invalid plan or price ID not configured for: {plan}")

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
        }
    )
    return session

async def handle_stripe_webhook(payload: bytes, sig_header: str):
    """
    Processes Stripe webhooks to update user subscription status.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise ValueError("Invalid payload")
    except stripe.error.SignatureVerificationError:
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
    # Retrieve user by subscription ID and downgrade
    from .models import User
    user = await User.find_one(User.stripe_subscription_id == subscription.id)
    if user:
        user.plan = 'solo' # Downgrade to free tier
        user.stripe_subscription_id = None
        await user.save()
        await log_event(user.email, "subscription_cancelled", "warning", "Subscription ended, downgraded to solo")
