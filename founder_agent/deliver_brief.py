# founder_agent/deliver_brief.py
import asyncio, os, json, base64, httpx
from datetime import datetime
from dotenv import load_dotenv
import logging
import sys

from google.adk.runners import InMemoryRunner
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.message import EmailMessage

from google import genai
from google.genai import types

from founder_agent.db.connection import connect_db
from founder_agent.db.crud import (
    get_all_active_users, update_last_brief,
    save_brief, get_yesterday_brief, log_event
)
from founder_agent.whatsapp_deliver import send_whatsapp_message
from founder_agent.sub_agents.revenue_agent import get_stripe_revenue
from founder_agent.sub_agents.inbox_agent import get_urgent_emails
from founder_agent.sub_agents.competitor_agent import browse_competitor_news
from founder_agent.sub_agents.calendar_agent import get_calendar_events

load_dotenv()

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
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

async def send_brief_email(user, brief_text: str):
    logger.info(f"Preparing email for {user.email}")
    if not user.gmail_token:
        logger.error(f"Missing gmail_token for {user.email}")
        return

    try:
        def _send():
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
            service.users().messages().send(userId="me", body={'raw': encoded_message}).execute()
            
        await asyncio.to_thread(_send)
        logger.info(f"SUCCESS! Brief sent to {user.email}")
    except Exception as e:
        logger.error(f"Error sending email to {user.email}: {e}")
        raise

from founder_agent.db.security import sanitize_external_content

async def run_brief_for_user(user):
    """Runs the full brief pipeline for a single user."""
    logger.info("Running brief generation", extra={"user_email": user.email})

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

    # Orchestrate tools directly to avoid Global State Mutation (os.environ)
    try:
        results = await asyncio.gather(
            get_stripe_revenue(user.stripe_key),
            get_urgent_emails(user.gmail_token),
            get_calendar_events(user.gmail_token),
            return_exceptions=True
        )
        revenue_data, inbox_data, calendar_data = results
        # Handle exceptions in gather
        if isinstance(revenue_data, Exception): revenue_data = {"error": str(revenue_data)}
        if isinstance(inbox_data, Exception): inbox_data = {"error": str(inbox_data)}
        if isinstance(calendar_data, Exception): calendar_data = {"error": str(calendar_data)}
    except Exception as e:
        logger.error(f"Failed to gather primary data: {e}")
        revenue_data, inbox_data, calendar_data = {}, {}, {}

    competitors = [c.strip() for c in user.competitor_list.split(',')]
    competitor_news = []
    # Concurrently fetch competitor data (limited by TinyFish/Network)
    comp_results = await asyncio.gather(
        *[browse_competitor_news(comp) for comp in competitors],
        return_exceptions=True
    )
    for res in comp_results:
        if not isinstance(res, Exception):
            # 🛡️ SANITIZE EXTERNAL CONTENT (T4 Defense)
            if isinstance(res, dict):
                # We sanitize the values (headlines/descriptions/updates)
                for key, val in res.items():
                    if isinstance(val, str):
                        res[key] = sanitize_external_content(val)
            competitor_news.append(res)

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
    
    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "foundtel-production"),
        location="us-central1"
    )

    try:
        safety_settings = [
            types.SafetySetting(category=c, threshold=types.SafetyThreshold.BLOCK_MEDIUM_AND_ABOVE)
            for c in [
                types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
            ]
        ]

        # Note: genai client.models.generate_content might still be blocking 
        # unless used with its async counterpart if available in ADK version.
        # Assuming we need to run it in thread if it blocks the loop.
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                safety_settings=safety_settings,
            )
        )
        brief_text = response.text
    except Exception as e:
        logger.warning(f"Vertex AI failed for {user.email}, falling back to Public API: {e}")
        async with httpx.AsyncClient() as h_client:
            GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_instruction}]}
            }
            resp = await h_client.post(url, json=payload, timeout=30.0)
            resp_data = resp.json()
            brief_text = resp_data['candidates'][0]['content']['parts'][0]['text']

    # Save and Deliver
    await save_brief(user.email, brief_text, emails_seen, comp_headlines)
    
    delivery_tasks = [send_brief_email(user, brief_text)]
    if user.whatsapp_number:
        delivery_tasks.append(asyncio.to_thread(send_whatsapp_message, user.whatsapp_number, brief_text))
    
    await asyncio.gather(*delivery_tasks, return_exceptions=True)
    await update_last_brief(user.email)
    await log_event(user.email, 'brief_sent', 'success')
    logger.info(f"Brief pipeline completed for {user.email}")

async def run_all_briefs():
    """Main entry point — runs briefs concurrently with safety limits."""
    await connect_db()
    
    semaphore = asyncio.Semaphore(5) # Max 5 concurrent users to avoid resource exhaustion
    
    async def _safe_run(user):
        async with semaphore:
            try:
                await run_brief_for_user(user)
            except Exception as e:
                await log_event(user.email, 'brief_error', 'failure', str(e))
                logger.error(f"Failed brief for {user.email}: {e}")

    tasks = []
    async for user in get_all_active_users():
        tasks.append(_safe_run(user))
    
    if tasks:
        logger.info(f"Triggering concurrent briefs for {len(tasks)} users")
        await asyncio.gather(*tasks)
    else:
        logger.info("No active users found to brief.")

if __name__ == '__main__':
    asyncio.run(run_all_briefs())
