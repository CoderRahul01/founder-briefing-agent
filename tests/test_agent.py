import asyncio
from founder_agent.agent import root_agent

async def main():
    print("Testing root_agent as async iter...")
    response_text = ""
    # Usually ADK LlmAgent when run via run_live returns an async generator 
    # but the way to invoke it normally might be via `run()` which blocks or `run_async()`
    # Let's see if we can just wrap it in a list comprehension or look at its events
    generator = root_agent.run_live("say hello")
    async for event in generator:
        if hasattr(event, 'text'):
            response_text += event.text
            print(f"event text: {event.text}")
            
    print(f"Final text is: {response_text}")

if __name__ == "__main__":
    asyncio.run(main())
