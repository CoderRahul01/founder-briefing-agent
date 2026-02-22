from typing import Optional, List
from datetime import datetime, date, timedelta
from .models import User, Brief, AuditLog


# ── USERS ────────────────────────────────────────────────────

async def create_user(email: str, stripe_key: str = None,
                      gmail_token: str = None,
                      competitor_list: str = 'Linear,Notion,Asana',
                      plan: str = 'solo') -> User:
    user = User(
        email=email,
        stripe_key=stripe_key,
        gmail_token=gmail_token,
        competitor_list=competitor_list,
        delivery_email=email,
        plan=plan
    )
    await user.insert()
    return user


async def get_user(email: str) -> Optional[User]:
    return await User.find_one(User.email == email)


async def get_all_active_users() -> List[User]:
    return await User.find(User.is_active == True).to_list()


async def update_last_brief(email: str):
    user = await get_user(email)
    if user:
        user.last_brief_at = datetime.utcnow()
        await user.save()


async def update_gmail_token(email: str, token_json: str):
    user = await get_user(email)
    if user:
        user.gmail_token = token_json
        await user.save()


# ── BRIEFS (Memory) ──────────────────────────────────────────

async def save_brief(user_email: str, brief_text: str,
                     emails_seen: list, competitor_headlines: list,
                     revenue_summary: str = None) -> Brief:
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


async def get_yesterday_brief(user_email: str) -> Optional[Brief]:
    yesterday = str(date.today() - timedelta(days=1))
    return await Brief.find_one(
        Brief.user_email == user_email,
        Brief.date == yesterday
    )


async def get_brief_history(user_email: str, limit: int = 7) -> List[Brief]:
    return await Brief.find(
        Brief.user_email == user_email
    ).sort(-Brief.created_at).limit(limit).to_list()


# ── AUDIT LOGS ────────────────────────────────────────────────

async def log_event(user_email: str, event_type: str,
                    status: str, message: str = None, metadata: dict = {}):
    log = AuditLog(
        user_email=user_email,
        event_type=event_type,
        status=status,
        message=message,
        metadata=metadata
    )
    await log.insert()

async def get_recent_brief_count(user_email: str, hours: int = 24) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    # Count success events of type 'brief_sent' or 'manual_brief_triggered'
    count = await AuditLog.find(
        AuditLog.user_email == user_email,
        AuditLog.event_type == 'brief_sent',
        AuditLog.status == 'success',
        AuditLog.created_at >= cutoff
    ).count()
    return count
