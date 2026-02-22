import asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to sys.path to allow importing from founder_agent
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

async def main():
    from founder_agent.db.connection import connect_db
    from founder_agent.db.crud import create_user, get_user

    await connect_db()

    existing = await get_user('rahulpandey.creates@gmail.com')
    if existing:
        print(f'Already exists! Plan: {existing.plan}')
        return

    # Fetch token from the secrets location we set up earlier
    # Fetch token from the secrets location
    token_path = Path(__file__).parent.parent / "founder_agent" / "secrets" / "token.json"
    try:
        with open(token_path) as f:
            token_str = f.read()
    except FileNotFoundError:
        print("token.json not found in secrets/. Please authenticate first.")
        return

    user = await create_user(
        email='rahulpandey.creates@gmail.com',
        stripe_key=os.getenv('STRIPE_SECRET_KEY', ''),
        gmail_token=token_str,
        competitor_list=os.getenv('COMPETITOR_LIST', 'Linear,Notion,Asana'),
        plan='founder'
    )
    print(f'User created in MongoDB! ID: {user.id}')

if __name__ == '__main__':
    asyncio.run(main())
