import asyncio, os
from dotenv import load_dotenv
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
    token_path = os.path.join(os.path.dirname(__file__), 'secrets', 'token.json')
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
