import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from founder_agent.sub_agents.revenue_agent import revenue_agent
from founder_agent.sub_agents.inbox_agent import inbox_agent
from founder_agent.sub_agents.competitor_agent import competitor_agent

from founder_agent.db.crud import get_user, log_event

today = datetime.date.today().strftime('%A, %B %d %Y')

# Define the base coordinator agent
_root_agent = LlmAgent(
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

async def root_agent(event):
    """
    Wrapper for A2A multi-tenancy.
    Extracts user identity and executes the agent with specific context.
    """
    user_email = event.user_id or "default@foundtel.com" # Fallback for local testing
    
    # 1. Fetch User Context
    user = await get_user(user_email)
    if not user:
        return f"Error: User {user_email} not found in Foundtel database."
    
    if not user.is_active:
        return f"Error: User account {user_email} is inactive."

    # 2. Plan-based Gating (Monetization Hook)
    # Example: Only 'founder' plan can use competitor radar
    is_competitor_radar_requested = "competitor" in str(event.content).lower()
    if is_competitor_radar_requested and user.plan == "solo":
         return "Upgrade to FOUNDER plan to access Competitor Radar via A2A."

    # 3. Plan-based Output Depth via Context Injection
    depth_instruction = (
        "Focus on high-level headlines and surface-level summaries. Do not perform deep strategic analysis. Keep the brief concise."
    ) if user.plan == "solo" else (
        "Perform deep strategic breakdown: analyze product direction, hiring signals, pricing shifts, and positioning changes. Provide actionable founder-level strategy."
    )
    
    contextual_prompt = f"""
    Internal Context Settings:
    User Plan: {user.plan.upper()}
    Instruction Depth: {depth_instruction}
    
    User Query: {event.content}
    """

    # 4. Execution & Audit
    try:
        # In a real ADK multi-tenant setup, we would pass 'user' to the sub-agents' tool calls
        # For now, we simulate the orchestration
        await log_event(user_email, "a2a_trigger", "success", "Agent called via A2A", metadata={"plan": user.plan})
        
        # Execute the underlying coordinator with the augmented prompt
        response = await _root_agent.run(contextual_prompt)
        return response
    except Exception as e:
        await log_event(user_email, "a2a_trigger", "error", str(e))
        return f"Internal Error: {str(e)}"
