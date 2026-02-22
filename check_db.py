import asyncio
import os
from dotenv import load_dotenv
from founder_agent.db.connection import connect_db
from founder_agent.db.models import User, Brief

load_dotenv()

async def check():
    await connect_db()
    users = await User.find_all().to_list()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"User: {u.email}, Active: {u.is_active}, WhatsApp: {u.whatsapp_number}")
        
    briefs = await Brief.find_all().to_list()
    print(f"Total briefs: {len(briefs)}")
    for b in briefs:
        print(f"Brief for {b.user_email} on {b.date} - Status: {b.delivery_status}")
        print(f"Text snippet: {b.brief_text[:50]}")

if __name__ == "__main__":
    asyncio.run(check())
