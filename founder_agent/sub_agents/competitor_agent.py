import os, requests, time, json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv
load_dotenv()

TINYFISH_BASE = 'https://agent.tinyfish.ai/v1/automation/run-sse'
TINYFISH_HEADERS = {
    'X-API-Key': os.getenv('TINYFISH_API_KEY'),
    'Content-Type': 'application/json'
}

def _run_tinyfish(url: str, goal: str, competitor_name: str) -> dict:
    """Helper to run TinyFish SSE stream and parse the result."""
    try:
        response = requests.post(
            TINYFISH_BASE,
            headers=TINYFISH_HEADERS,
            json={'url': url, 'goal': goal},
            stream=True,
            timeout=15
        )
    except requests.exceptions.Timeout:
        return {'status': 'timeout_fetching', 'competitor': competitor_name}
    except Exception as e:
        return {'status': 'error', 'competitor': competitor_name, 'error': str(e)}

    result = {}
    start_time = time.time()
    for line in response.iter_lines():
        if time.time() - start_time > 60:
            print(f"Timeout waiting for TinyFish SSE for {competitor_name}")
            break
        if line:
            decoded = line.decode('utf-8')
            if '"type": "COMPLETE"' in decoded:
                try:
                    data = json.loads(decoded.replace('data: ','').strip())
                    result = data.get('resultJson', {})
                except Exception:
                    pass
                break
    return result or {'status': 'no_data_found', 'competitor': competitor_name}


def browse_competitor_news(competitor_name: str) -> dict:
    """Uses TinyFish to browse a competitors blog/news and extract recent updates."""
    url = f'https://{competitor_name.lower()}.com/blog'
    goal = f'Find any new product launches or major announcements from {competitor_name} in the last 30 days. Return as JSON with keys: update, significance.'
    return _run_tinyfish(url, goal, competitor_name)


def scrape_competitor_pricing(competitor_name: str) -> dict:
    """Uses TinyFish to extract the competitor's current pricing."""
    url = f'https://{competitor_name.lower()}.com/pricing'
    goal = f'Extract the main pricing tiers, exact monthly price, and 1 core differentiator for each tier. Return as JSON.'
    return _run_tinyfish(url, goal, competitor_name)


def scrape_competitor_jobs(competitor_name: str) -> dict:
    """Uses TinyFish to check the competitor's careers page to see where they are hiring."""
    url = f'https://{competitor_name.lower()}.com/careers'
    goal = f'Find the top 3 open engineering or product roles at {competitor_name}. This indicates what they are building next. Return as JSON.'
    return _run_tinyfish(url, goal, competitor_name)


news_tool    = FunctionTool(func=browse_competitor_news)
pricing_tool = FunctionTool(func=scrape_competitor_pricing)
jobs_tool    = FunctionTool(func=scrape_competitor_jobs)

competitor_agent = LlmAgent(
    name='competitor_agent',
    model='gemini-2.0-flash',
    description='Uses TinyFish to browse competitor sites and extract strategic intelligence (news, pricing, hiring).',
    instruction='''
    You are a competitive intelligence analyst.
    For each competitor in the COMPETITOR_LIST env var:
    1. Check their news (browse_competitor_news)
    2. Check their pricing (scrape_competitor_pricing)
    3. Check what roles they are hiring for (scrape_competitor_jobs)
    
    Synthesize this into a structured analysis.
    Return 1-2 bullet points per competitor highlighting what they launched, how much they charge, or what their hiring implies about their strategy.
    Keep it extremely concise and action-oriented for the founder.
    ''',
    tools=[news_tool, pricing_tool, jobs_tool],
)
