# founder_agent/sub_agents/revenue_agent.py
import os, httpx
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv
import time

load_dotenv()

async def get_stripe_revenue(stripe_key: str = None) -> dict:
    """Fetches MRR and recent customer activity from Stripe."""
    # Use user-specific key if provided, else fallback to global env (Safely)
    effective_key = stripe_key or os.getenv("STRIPE_SECRET_KEY")
    if not effective_key:
        return {'error': 'No Stripe key available'}
        
    headers = {'Authorization': f'Bearer {effective_key}'} 
    
    # Get recent charges (last 7 days)
    seven_days_ago = int(time.time()) - 604800
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                'https://api.stripe.com/v1/charges',
                headers=headers,
                params={'limit': 20, 'created[gte]': seven_days_ago},
                timeout=10.0
            )
            resp.raise_for_status()
            charges = resp.json()
            
            data = charges.get('data', [])
            total = sum(c['amount'] for c in data if c.get('paid')) / 100
            return {
                'weekly_revenue_usd': total, 
                'recent_charges': len(data),
                'is_platform_key': not stripe_key # Track if we fell back
            }
        except Exception as e:
            return {'error': f"Stripe API error: {str(e)}"}

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
