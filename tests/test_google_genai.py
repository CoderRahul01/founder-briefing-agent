import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
os.environ['GEMINI_API_KEY'] = os.getenv('GOOGLE_API_KEY')

from founder_agent.sub_agents.revenue_agent import get_stripe_revenue
from founder_agent.sub_agents.inbox_agent import get_urgent_emails
from founder_agent.sub_agents.competitor_agent import browse_competitor_news, scrape_competitor_pricing
import datetime

today = datetime.date.today().strftime('%A, %B %d %Y')

instruction=f'''You are an elite chief of staff briefing a tech founder every morning.
Today is {today}. Call ALL tools first, then write the brief.

OUTPUT FORMAT:
GOOD MORNING BRIEF — {today}
💰 REVENUE PULSE: [2 sentences from get_stripe_revenue]
📬 INBOX PRIORITIES: [Top 3 from get_urgent_emails]
🔍 COMPETITOR RADAR: [Bullets from browse_competitor_news/scrape_competitor_pricing]
✅ ONE DECISION FOR TODAY: [Most important decision]
'''

client = genai.Client()
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=f"It is {today}. Please generate today's briefing.",
    config=types.GenerateContentConfig(
        system_instruction=instruction,
        tools=[get_stripe_revenue, get_urgent_emails, browse_competitor_news, scrape_competitor_pricing],
    ),
)
print("Response text successfully parsed!")
print(response.text)
