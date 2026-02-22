# founder_agent/deliver_brief.py  (fully updated)
import asyncio, os, json
from datetime import datetime
from dotenv import load_dotenv

from google.adk.runners import InMemoryRunner
from founder_agent.agent import root_agent

import logging
import sys

# Configure structured logging for GCP
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "time": datetime.utcnow().isoformat() + "Z",
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

logger = logging.getLogger("foundtel")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

from founder_agent.db.connection import connect_db
from founder_agent.db.crud import (
    get_all_active_users, update_last_brief,
    save_brief, get_yesterday_brief, log_event
)
from founder_agent.whatsapp_deliver import send_whatsapp_message

import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

load_dotenv()

def send_brief_email(user, brief_text: str):
    logger.info(f"Preparing email for {user.email}")
    try:
        # Reconstruct credentials from DB token
        creds_json = json.loads(user.gmail_token)
        creds = Credentials.from_authorized_user_info(creds_json)
        
        service = build('gmail', 'v1', credentials=creds)

        message = EmailMessage()
        message.set_content(brief_text)
        message['To'] = user.delivery_email or user.email
        message['From'] = user.email
        today_str = datetime.today().strftime('%A, %B %d %Y')
        message['Subject'] = f"GOOD MORNING BRIEF — {today_str}"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        print(f"Sending email via Gmail API to {user.delivery_email or user.email}...")
        service.users().messages().send(userId="me", body=create_message).execute()
        print("SUCCESS! Brief sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise e

async def run_brief_for_user(user):
    """Runs the full brief pipeline for a single user."""
    logger.info(f"Running brief generation for user", extra={"user": user.email})

    # Load yesterday for memory context
    yesterday = await get_yesterday_brief(user.email)
    memory_context = ''
    if yesterday:
        memory_context = f'''
YESTERDAY ({yesterday.date}):
Emails shown: {', '.join(yesterday.emails_seen[:3])}
Competitor headlines: {', '.join(yesterday.competitor_headlines[:3])}
Do NOT repeat these items today.
'''

    # Set this user's env vars for sub-agents
    os.environ['USER_STRIPE_KEY']    = user.stripe_key or ''
    os.environ['COMPETITOR_LIST']    = user.competitor_list
    os.environ['MEMORY_CONTEXT']     = memory_context
    os.environ['GMAIL_OAUTH_TOKEN']  = user.gmail_token

    from founder_agent.sub_agents.revenue_agent import get_stripe_revenue
    from founder_agent.sub_agents.inbox_agent import get_urgent_emails
    from founder_agent.sub_agents.competitor_agent import browse_competitor_news
    from founder_agent.sub_agents.calendar_agent import get_calendar_events # Fetch tool directly for now
    import requests

    try:
        revenue_data = get_stripe_revenue()
    except Exception as e:
        revenue_data = {"error": str(e)}

    try:
        inbox_data = get_urgent_emails()
    except Exception as e:
        inbox_data = {"error": str(e)}

    try:
        calendar_data = get_calendar_events()
    except Exception as e:
        calendar_data = {"error": str(e)}

    competitors = [c.strip() for c in user.competitor_list.split(',')]
    competitor_news = []
    for comp in competitors:
        try:
            news = browse_competitor_news(comp)
            competitor_news.append(news)
        except Exception:
            pass

    # Extract items seen
    emails_seen = [e.get('subject') for e in inbox_data.get('top_emails', []) if isinstance(e, dict)]
    comp_headlines = [n.get('headline') for n in competitor_news if isinstance(n, dict) and n.get('headline')]
    
    system_instruction = f'''
    You are an elite chief of staff briefing a tech founder every morning.
    Today is {datetime.today().strftime('%A, %B %d %Y')}.
    {memory_context}

    INSTRUCTIONS:
    1. Review the data for accuracy. If a sub-agent failed, omit that section gracefully.
    2. Tone: Professional, elite, concise, biased towards action.
    3. Check for hallucinations: Do not invent revenue or competitors.

    OUTPUT FORMAT:
    GOOD MORNING BRIEF — {datetime.today().strftime('%A, %B %d %Y')}
    🗓️ TODAY'S SCHEDULE: [Summarize top 2-3 important calendar events]
    💰 REVENUE PULSE: [2 sentences describing the revenue]
    📬 INBOX PRIORITIES: [Top 3 from inbox data]
    🔍 COMPETITOR RADAR: [Bullets from competitor data]
    ✅ ONE DECISION FOR TODAY: [Most important decision based on data]
    '''
    
    prompt = f"""
    Here is the data for today's briefing:
    
    Calendar Events: {json.dumps(calendar_data)}
    Revenue Data: {json.dumps(revenue_data)}
    Inbox Data: {json.dumps(inbox_data)}
    Competitor News: {json.dumps(competitor_news)}
    
    Please generate the daily brief.
    """
    
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "foundtel-onboarding-161455282267"),
        location="us-central1"
    )

    try:
        # Implementation of Safety Settings for Free Tier/Production Policy
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.SafetyThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.SafetyThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.SafetyThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.SafetyThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2, # Lowered for accuracy/guardrail
                safety_settings=safety_settings,
            )
        )
        brief_text = response.text
        logger.info("Successfully generated brief using Vertex AI")
    except Exception as e:
        logger.error(f"Vertex AI generation failed: {e}", exc_info=True)
        # Fallback to public API if vertex fails or isn't enabled yet
        GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]}
        }
        resp = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        brief_text = resp.json()['candidates'][0]['content']['parts'][0]['text']

    # Save brief to MongoDB (powers memory tomorrow)
    await save_brief(
        user_email=user.email,
        brief_text=brief_text,
        emails_seen=emails_seen,
        competitor_headlines=comp_headlines,
    )

    # Send the brief
    send_brief_email(user, brief_text)
    if user.whatsapp_number:
        send_whatsapp_message(user.whatsapp_number, brief_text)
        
    await update_last_brief(user.email)
    await log_event(user.email, 'brief_sent', 'success')
    print(f'Brief sent to {user.email}')


async def run_all_briefs():
    """Main entry point — runs brief for every active user."""
    await connect_db()                          # connect to MongoDB Atlas
    users = await get_all_active_users()
    print(f'Running briefs for {len(users)} users...')
    for user in users:
        try:
            await run_brief_for_user(user)
        except Exception as e:
            await log_event(user.email, 'brief_error', 'failure', str(e))
            print(f'Failed for {user.email}: {e}')

if __name__ == '__main__':
    asyncio.run(run_all_briefs())
