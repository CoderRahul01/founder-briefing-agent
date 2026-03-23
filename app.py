from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

from founder_agent.db.connection import connect_db
from founder_agent.db.crud import get_user, get_brief_history
from founder_agent.db.models import User
from founder_agent.dashboard_utils import (
    DIGEST_CONCISE,
    DIGEST_DEEP,
    DAILY_MODE,
    WEEKDAY_MODE,
    compute_next_brief_label,
    export_briefs_as_markdown,
    filter_briefs_by_query,
    normalize_csv_list,
)
from founder_agent.deliver_brief import run_brief_for_user, run_all_briefs
from founder_agent.a2a_exposure import a2a_app
from founder_agent.db.stripe_service import create_checkout_session, handle_stripe_webhook

load_dotenv()

app = FastAPI()
# Mount A2A protocol exposure
app.mount("/a2a", a2a_app)

# Use a static secret key from env or fallback for persistent sessions across restarts
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "foundtel-secure-session-secret-999"))

templates = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly',
        'prompt': 'consent',
        'access_type': 'offline'
    }
)


@app.on_event("startup")
async def startup_event():
    await connect_db()


# -- Authentication Dependency --
async def get_current_user(request: Request):
    email = request.session.get("user_email")
    if not email:
        return None
    return await get_user(email)


def login_required(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=302, detail="Not logged in", headers={"Location": "/login"})
    return user


# -- Presentation Helpers --
def parse_brief_sections(brief_text: str):
    sections = []
    current = None
    for raw_line in brief_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line[:1] in {"🗓", "💰", "📬", "🔍", "✅", "🤝", "🌱"} and ":" in line:
            heading, body = line.split(":", 1)
            current = {"heading": heading.strip(), "body": body.strip()}
            sections.append(current)
        elif current:
            current["body"] = f"{current['body']} {line}".strip()
    return sections


def summarize_brief(brief_text: str):
    cleaned = " ".join(part.strip() for part in brief_text.splitlines() if part.strip())
    return cleaned[:180] + ("..." if len(cleaned) > 180 else "")


def build_dashboard_context(user: User, briefs, search_query: str = ""):
    competitor_names = normalize_csv_list(user.competitor_list or "")
    latest_brief = briefs[0] if briefs else None
    latest_sections = parse_brief_sections(latest_brief.brief_text) if latest_brief else []
    filtered_briefs = filter_briefs_by_query(briefs, search_query)

    manual_remaining = "Unlimited" if user.plan != 'solo' else max(0, 1 - (user.manual_triggers_used or 0))
    integration_status = [
        {
            "name": "Gmail",
            "status": "Connected" if user.gmail_token else "Needs attention",
            "tone": "blue",
        },
        {
            "name": "Stripe",
            "status": "Connected" if user.stripe_key else "Optional",
            "tone": "indigo",
        },
        {
            "name": "WhatsApp",
            "status": "Connected" if user.whatsapp_number else ("Pro only" if user.plan == 'solo' else "Optional"),
            "tone": "emerald",
        },
    ]

    founder_nudges = [
        {
            "title": "Lead with clarity",
            "body": "Start the day by sharing one sentence with your team: what matters most, what can wait, and what success looks like by tonight.",
        },
        {
            "title": "Protect your energy",
            "body": "Leave one 30-minute block unscheduled for recovery or deep thinking. The brief is strongest when it supports your judgment, not your overload.",
        },
        {
            "title": "Strengthen a relationship",
            "body": "Reply to one investor, teammate, or customer with warmth and specificity before lunch. Tiny touches compound into trust.",
        },
    ]

    briefing_days = getattr(user, "briefing_days", WEEKDAY_MODE)
    briefing_time = getattr(user, "briefing_time", "07:00")
    digest_style = getattr(user, "digest_style", DIGEST_CONCISE)

    return {
        "competitor_names": competitor_names,
        "competitor_count": len(competitor_names),
        "latest_brief": latest_brief,
        "latest_sections": latest_sections,
        "latest_summary": summarize_brief(latest_brief.brief_text) if latest_brief else None,
        "brief_count": len(briefs),
        "filtered_briefs": filtered_briefs,
        "brief_search_query": search_query,
        "manual_remaining": manual_remaining,
        "next_brief_label": compute_next_brief_label(datetime.utcnow(), briefing_days, briefing_time),
        "integration_status": integration_status,
        "focus_question": "What conversation would make today feel meaningfully better by 5 PM?",
        "morning_message": (
            "You are not behind—you are entering the day with context, momentum, and a clearer point of view."
            if latest_brief else
            "Your first brief is on the way. Once it lands, this space will help you turn information into calm, decisive action."
        ),
        "founder_nudges": founder_nudges,
        "delivery_preferences": {
            "email": user.delivery_email or user.email,
            "briefing_days": briefing_days,
            "briefing_time": briefing_time,
            "digest_style": digest_style,
        },
        "strategy_snapshot": {
            "focus": (user.strategic_focus or "").strip(),
            "contacts": normalize_csv_list(user.priority_contacts or ""),
        },
        "digest_style_label": "Deep strategic analysis" if digest_style == DIGEST_DEEP else "Concise founder summary",
    }


# -- Routes --
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login")
async def login(request: Request):
    redirect_uri = str(request.url_for('auth_callback'))
    if "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        access_type='offline',
        prompt='consent'
    )


@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        return {"error": f"OAuth Error: {str(e)}"}

    user_info = token.get('userinfo')
    if not user_info:
        return {"error": "Failed to get user info."}

    email = user_info.get("email")
    if not email:
        return {"error": "Email not found in user info."}

    existing_user = await get_user(email)

    refresh_token = token.get("refresh_token")
    if not refresh_token and existing_user and existing_user.gmail_token:
        try:
            old_creds = json.loads(existing_user.gmail_token)
            refresh_token = old_creds.get("refresh_token")
        except Exception:
            pass

    creds_dict = {
        "token": token.get("access_token"),
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]
    }

    token_str = json.dumps(creds_dict)

    if existing_user:
        existing_user.gmail_token = token_str
        await existing_user.save()
        user = existing_user
    else:
        user = User(
            email=email,
            gmail_token=token_str,
            competitor_list="Linear,Notion,Asana",
            delivery_email=email,
            plan='solo'
        )
        await user.insert()
        if 'competitor_list' in request.session:
            user.competitor_list = request.session.pop('competitor_list')
            user.stripe_key = request.session.pop('stripe_key', '')
            user.whatsapp_number = request.session.pop('whatsapp_number', '')
            await user.save()

    request.session["user_email"] = email
    asyncio.create_task(background_brief(user))

    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, search: Optional[str] = None, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")

    briefs = await get_brief_history(user.email)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "briefs": briefs,
        **build_dashboard_context(user, briefs, search or ""),
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "allowed_delivery_modes": [WEEKDAY_MODE, DAILY_MODE],
        "allowed_digest_styles": [DIGEST_CONCISE, DIGEST_DEEP],
    })


@app.post("/update-settings")
async def update_settings(request: Request,
                          competitor_list: str = Form(...),
                          stripe_key: str = Form(""),
                          whatsapp_number: str = Form(""),
                          delivery_email: str = Form(""),
                          briefing_days: str = Form(WEEKDAY_MODE),
                          briefing_time: str = Form("07:00"),
                          digest_style: str = Form(DIGEST_CONCISE),
                          strategic_focus: str = Form(""),
                          priority_contacts: str = Form(""),
                          user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")

    competitor_limit = 3 if user.plan == 'solo' else None
    cleaned_competitors = normalize_csv_list(competitor_list, limit=competitor_limit)
    cleaned_contacts = normalize_csv_list(priority_contacts, limit=6)
    warning_message = None

    if user.plan == 'solo' and len(normalize_csv_list(competitor_list)) > 3:
        warning_message = "Solo plan supports up to 3 competitors. Upgrade to Pro to track unlimited companies."

    if user.plan == 'solo' and whatsapp_number.strip():
        whatsapp_number = ""
        if not warning_message:
            warning_message = "WhatsApp delivery is only available in the Pro tier."

    if briefing_days not in {WEEKDAY_MODE, DAILY_MODE}:
        briefing_days = WEEKDAY_MODE

    if digest_style not in {DIGEST_CONCISE, DIGEST_DEEP}:
        digest_style = DIGEST_CONCISE

    user.competitor_list = ",".join(cleaned_competitors)
    user.stripe_key = stripe_key or None
    user.whatsapp_number = whatsapp_number.strip() or None
    user.delivery_email = (delivery_email or user.email).strip()
    user.briefing_days = briefing_days
    user.briefing_time = briefing_time or "07:00"
    user.digest_style = digest_style
    user.strategic_focus = strategic_focus.strip() or None
    user.priority_contacts = ",".join(cleaned_contacts) if cleaned_contacts else None
    await user.save()

    if warning_message:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": user,
            "error": warning_message,
            "allowed_delivery_modes": [WEEKDAY_MODE, DAILY_MODE],
            "allowed_digest_styles": [DIGEST_CONCISE, DIGEST_DEEP],
        })

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/briefs/export", response_class=PlainTextResponse)
async def export_briefs(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")

    briefs = await get_brief_history(user.email, limit=30)
    content = export_briefs_as_markdown(user.email, briefs)
    headers = {"Content-Disposition": 'attachment; filename="foundtel-briefs.md"'}
    return PlainTextResponse(content, headers=headers)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


# -- Background Tasks --
async def background_brief(user):
    print(f"Generating initial background brief for {user.email}")
    try:
        await run_brief_for_user(user)
    except Exception as e:
        print(f"Background brief failed: {e}")


@app.post("/trigger-briefs-now")
async def trigger_brief_now(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")

    from founder_agent.db.crud import log_event

    now = datetime.utcnow()

    if user.manual_trigger_reset_at is None or now >= user.manual_trigger_reset_at:
        user.manual_triggers_used = 0
        user.manual_trigger_reset_at = now + timedelta(days=7)

    if user.plan == "solo" and user.manual_triggers_used >= 1:
        await log_event(user.email, "upgrade_prompt_shown", "manual_trigger_limit", metadata={"current_count": user.manual_triggers_used})
        briefs = await get_brief_history(user.email)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "briefs": briefs,
            "error": "Manual trigger limit reached (1/week on Free tier). Upgrade to Founder for unlimited on-demand briefs.",
            **build_dashboard_context(user, briefs),
        })

    user.manual_triggers_used += 1
    await user.save()

    await run_brief_for_user(user)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/trigger-briefs")
async def trigger_briefs(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {os.getenv('CRON_SECRET', 'foundtel-cron-secret-123')}":
        return {"error": "Unauthorized"}

    await run_all_briefs()
    return {"status": "ok"}


@app.get("/checkout/{plan_name}")
async def checkout(plan_name: str, request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")

    success_url = str(request.url_for('dashboard'))
    cancel_url = str(request.url_for('dashboard'))
    session = await create_checkout_session(user.email, plan_name, success_url, cancel_url)
    return RedirectResponse(url=session.url, status_code=303)


@app.post('/stripe-webhook')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    await handle_stripe_webhook(payload, sig_header)
    return {"received": True}
