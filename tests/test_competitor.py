from founder_agent.sub_agents.competitor_agent import browse_competitor_news
from dotenv import load_dotenv

load_dotenv()
try:
    print("Testing Linear...")
    res = browse_competitor_news("Linear")
    print(res)
except Exception as e:
    print(f"Error: {e}")
