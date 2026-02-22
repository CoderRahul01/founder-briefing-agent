import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from founder_agent.agent import root_agent

# Define a professional A2A agent card for discovery and monetization
foundtel_agent_card = AgentCard(
    name="foundtel-chief-of-staff",
    url=os.getenv("A2A_BASE_URL", "http://localhost:8001"),
    description="Proactive AI Chief of Staff. Synthesizes revenue, inbox, and competitor data into a 3-minute morning brief.",
    version="1.0.0",
    capabilities={
        "multi_tenant": True,
        "identity_context": True,
        "monetization": "usage-based"
    },
    skills=[
        {
            "name": "revenue_pulse",
            "description": "Synthesize Stripe MRR and revenue trends."
        },
        {
            "name": "inbox_priorities",
            "description": "Categorize and surface urgent emails from Gmail."
        },
        {
            "name": "competitor_radar",
            "description": "Track competitor blogs and product changelogs."
        }
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=True
)

# Create the A2A compatible app with the custom card
a2a_app = to_a2a(root_agent, agent_card=foundtel_agent_card)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
