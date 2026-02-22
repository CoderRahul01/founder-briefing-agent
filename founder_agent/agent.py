import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from founder_agent.sub_agents.revenue_agent import revenue_agent
from founder_agent.sub_agents.inbox_agent import inbox_agent
from founder_agent.sub_agents.competitor_agent import competitor_agent

today = datetime.date.today().strftime('%A, %B %d %Y')

root_agent = LlmAgent(
    name='founder_briefing_coordinator',
    model='gemini-2.0-flash',
    description='Chief of staff AI that produces a daily founder intelligence brief.',
    instruction=f'''
    You are an elite chief of staff briefing a tech founder every morning.
    Today is {today}. Call ALL sub-agents first, then write the brief.

    OUTPUT FORMAT:
    GOOD MORNING BRIEF — {today}
    💰 REVENUE PULSE: [2 sentences from revenue_agent]
    📬 INBOX PRIORITIES: [Top 3 from inbox_agent]
    🔍 COMPETITOR RADAR: [Bullets from competitor_agent]
    ✅ ONE DECISION FOR TODAY: [Most important decision]
    ''',
    tools=[
        AgentTool(agent=revenue_agent),
        AgentTool(agent=inbox_agent),
        AgentTool(agent=competitor_agent),
    ],
)
