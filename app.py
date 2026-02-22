from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import os
import json
import asyncio
from dotenv import load_dotenv

from founder_agent.db.connection import connect_db
from founder_agent.db.crud import get_user, get_brief_history
from founder_agent.db.models import User
from founder_agent.deliver_brief import run_brief_for_user, run_all_briefs

load_dotenv()

app = FastAPI()
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

# -- Routes --

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login")
async def login(request: Request):
    # This route is used to initiate the OAuth flow
    # In our current setup, the "Connect with Google" button on home/login page triggers this
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
        # Initial onboarding defaults
        user = User(
            email=email,
            gmail_token=token_str,
            competitor_list="Linear,Notion,Asana",
            delivery_email=email,
            plan='solo'
        )
        await user.insert()
        # Handle existing registration session data if it was a new sign up flow
        if 'competitor_list' in request.session:
            user.competitor_list = request.session.pop('competitor_list')
            user.stripe_key = request.session.pop('stripe_key', '')
            user.whatsapp_number = request.session.pop('whatsapp_number', '')
            await user.save()

    # Set persistent session
    request.session["user_email"] = email
    
    # Trigger first brief in background (if it's the very first time)
    # For now, we'll just run it to ensure user has something to see
    asyncio.create_task(background_brief(user))
    
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    
    briefs = await get_brief_history(user.email)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "briefs": briefs
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})

@app.post("/update-settings")
async def update_settings(request: Request, 
                          competitor_list: str = Form(...),
                          stripe_key: str = Form(""),
                          whatsapp_number: str = Form(""),
                          user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/")
    
    user.competitor_list = competitor_list
    user.stripe_key = stripe_key
    user.whatsapp_number = whatsapp_number
    await user.save()
    
    return RedirectResponse(url="/dashboard", status_code=303)

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
    
    from founder_agent.db.crud import get_recent_brief_count
    count = await get_recent_brief_count(user.email)
    
    if count >= 3:
        # Show an error or flash message on the dashboard
        briefs = await get_brief_history(user.email)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "briefs": briefs,
            "error": "Daily manual limit reached (3/day). Please wait until tomorrow for your next brief."
        })

    await run_brief_for_user(user)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/trigger-briefs")
async def trigger_briefs(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {os.getenv('CRON_SECRET', 'foundtel-cron-secret-123')}":
        return {"error": "Unauthorized"}
        
    await run_all_briefs()
    return {"status": "Daily briefs triggered successfully"}
