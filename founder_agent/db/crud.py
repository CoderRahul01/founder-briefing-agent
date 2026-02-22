from typing import Optional, List, AsyncGenerator
from datetime import datetime, date, timedelta
from .models import User, Brief, AuditLog
from .security import encrypt_token, decrypt_token
import logging

logger = logging.getLogger(__name__)

# ── USERS ────────────────────────────────────────────────────

def _decrypt_user_tokens(user: User) -> User:
    """Helper to decrypt tokens if they are encrypted."""
    if user:
        if user.gmail_token:
            decrypted = decrypt_token(user.gmail_token)
            # If decryption fails but there's a token, it might be unencrypted (migration)
            if decrypted:
                user.gmail_token = decrypted
        if user.stripe_key:
            decrypted = decrypt_token(user.stripe_key)
            if decrypted:
                user.stripe_key = decrypted
    return user

async def create_user(email: str, stripe_key: str = None,
                      gmail_token: str = None,
                      competitor_list: str = 'Linear,Notion,Asana',
                      plan: str = 'solo') -> User:
    try:
        user = User(
            email=email,
            stripe_key=encrypt_token(stripe_key),
            gmail_token=encrypt_token(gmail_token),
            competitor_list=competitor_list,
            delivery_email=email,
            plan=plan
        )
        await user.insert()
        return _decrypt_user_tokens(user)
    except Exception as e:
        logger.error(f"Failed to create user {email}: {e}")
        raise

async def get_user(email: str) -> Optional[User]:
    try:
        user = await User.find_one(User.email == email)
        return _decrypt_user_tokens(user)
    except Exception as e:
        logger.error(f"Error fetching user {email}: {e}")
        return None

async def get_all_active_users(batch_size: int = 100) -> AsyncGenerator[User, None]:
    """Uses a generator with batching to avoid unbounded memory usage."""
    try:
        # Find all active users
        # We use a cursor to stream results if Beanie supports it, 
        # or we manually batch if needed.
        # Beanie's .find() returns a Query object that can be iterated asynchronously.
        async for user in User.find(User.is_active == True):
            yield _decrypt_user_tokens(user)
    except Exception as e:
        logger.error(f"Error streaming active users: {e}")

async def update_last_brief(email: str):
    try:
        user = await User.find_one(User.email == email)
        if user:
            user.last_brief_at = datetime.utcnow()
            await user.save()
    except Exception as e:
        logger.error(f"Error updating last brief for {email}: {e}")

async def update_gmail_token(email: str, token_json: str):
    try:
        user = await User.find_one(User.email == email)
        if user:
            user.gmail_token = encrypt_token(token_json)
            await user.save()
    except Exception as e:
        logger.error(f"Error updating gmail token for {email}: {e}")


# ── BRIEFS (Memory) ──────────────────────────────────────────

async def save_brief(user_email: str, brief_text: str,
                     emails_seen: list, competitor_headlines: list,
                     revenue_summary: str = None) -> Brief:
    try:
        brief = Brief(
            user_email=user_email,
            brief_text=brief_text,
            date=str(date.today()),
            emails_seen=emails_seen,
            competitor_headlines=competitor_headlines,
            revenue_summary=revenue_summary,
        )
        await brief.insert()
        return brief
    except Exception as e:
        logger.error(f"Error saving brief for {user_email}: {e}")
        raise


async def get_yesterday_brief(user_email: str) -> Optional[Brief]:
    try:
        yesterday = str(date.today() - timedelta(days=1))
        return await Brief.find_one(
            Brief.user_email == user_email,
            Brief.date == yesterday
        )
    except Exception as e:
        logger.error(f"Error fetching yesterday brief for {user_email}: {e}")
        return None


async def get_brief_history(user_email: str, limit: int = 7) -> List[Brief]:
    try:
        return await Brief.find(
            Brief.user_email == user_email
        ).sort(-Brief.created_at).limit(limit).to_list()
    except Exception as e:
        logger.error(f"Error fetching brief history for {user_email}: {e}")
        return []


# ── AUDIT LOGS ────────────────────────────────────────────────

async def log_event(user_email: str, event_type: str,
                    status: str, message: str = None, metadata: dict = {}):
    try:
        log = AuditLog(
            user_email=user_email,
            event_type=event_type,
            status=status,
            message=message,
            metadata=metadata,
            created_at=datetime.utcnow()
        )
        await log.insert()
    except Exception as e:
        # Don't raise on logging failure to avoid crashing the main flow, but log it locally
        print(f"CRITICAL: Failed to write to AuditLog: {e}")

async def get_recent_brief_count(user_email: str, hours: int = 24) -> int:
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        count = await AuditLog.find(
            AuditLog.user_email == user_email,
            AuditLog.event_type == 'brief_sent',
            AuditLog.status == 'success',
            AuditLog.created_at >= cutoff
        ).count()
        return count
    except Exception as e:
        logger.error(f"Error counting recent briefs for {user_email}: {e}")
        return 0
