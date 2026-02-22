# founder_agent/sub_agents/revenue_agent.py
import os, requests
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv
load_dotenv()

def get_stripe_revenue() -> dict:
    """Fetches MRR and recent customer activity from Stripe."""
    # Use user-specific key if provided, else fallback to global env
    stripe_key = os.environ.get("USER_STRIPE_KEY") or os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        return {'error': 'No Stripe key available'}
        
    headers = {'Authorization': f'Bearer {stripe_key}'} 
    # Get recent charges (last 7 days)
    charges = requests.get(
        'https://api.stripe.com/v1/charges',
        headers=headers,
        params={'limit': 20, 'created[gte]': int(__import__('time').time()) - 604800}
    ).json()
    total = sum(c['amount'] for c in charges.get('data',[]) if c['paid']) / 100
    return {'weekly_revenue_usd': total, 'recent_charges': len(charges.get('data',[]))}

revenue_tool = FunctionTool(func=get_stripe_revenue)

revenue_agent = LlmAgent(
    name='revenue_agent',
    model='gemini-2.0-flash',
    description='Analyzes Stripe revenue data and summarizes MRR and trends.',
    instruction='''
    You are a revenue analyst. Use get_stripe_revenue to fetch data.
    Return ONLY 2 sentences: current weekly revenue and one trend observation.
    Be specific with numbers. No fluff.
    ''',
    tools=[revenue_tool]
)
