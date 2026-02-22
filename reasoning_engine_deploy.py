import os
import vertexai
from vertexai.preview.reasoning_engines import ReasoningEngine
from founder_agent.agent import root_agent

def deploy_agent():
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "foundtel")
    location = "us-central1"
    staging_bucket = f"gs://{project}-reasoning-engine-staging"

    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    print("Deploying Founder Reasoning Engine...")
    
    # We wrap the existing root_agent logic into a Reasoning Engine deployment
    # For now, we deploy the class-based version of our agent
    remote_agent = ReasoningEngine.create(
        root_agent,
        requirements=[
            "google-genai",
            "vertexai",
            "fastapi",
            "authlib",
            "httpx",
            "motor",
            "beanie",
            "twilio",
            "google-api-python-client",
            "google-auth-oauthlib",
        ],
        display_name="FounderBriefingAgent",
    )
    
    print(f"Agent successfully deployed! ID: {remote_agent.resource_name}")
    return remote_agent.resource_name

if __name__ == "__main__":
    deploy_agent()
