import asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to sys.path to allow importing from founder_agent
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

async def check_logs():
    await connect_db()
    logs = await AuditLog.find_all().to_list()
    for log in logs:
        print(f"[{log.created_at}] {log.event_type} - {log.status} - {log.message}")

if __name__ == "__main__":
    asyncio.run(check_logs())
