import asyncio
from typing import AsyncGenerator
from google.adk.agents import LlmAgent, InvocationContext

agent = LlmAgent(name="test", model="gemini-2.0-flash", instruction="reply ok")

async def main():
    ctx = InvocationContext(session={"session_id": "test"}, session_service=None, agent=agent, invocation_id="1")
    # let's try the simplest
    print("Trying just string...")
    try:
        gen = agent.run_live("test")
        async for r in gen: print(r)
    except Exception as e: print(e)
    
if __name__ == "__main__":
    asyncio.run(main())
