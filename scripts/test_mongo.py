import asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to sys.path to allow importing from founder_agent
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

async def test():
    from founder_agent.db.connection import connect_db
    from founder_agent.db.crud import get_all_active_users

    await connect_db()
    users = await get_all_active_users()
    print(f'Active users in MongoDB: {len(users)}')
    for u in users:
        print(f'  -> {u.email} | plan: {u.plan} | active: {u.is_active}')

if __name__ == '__main__':
    asyncio.run(test())
