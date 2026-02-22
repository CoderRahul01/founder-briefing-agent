import os
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from .models import User, Brief, AuditLog

load_dotenv()


async def connect_db():
    """Initialize Beanie with MongoDB Atlas — call once at startup."""
    client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    await init_beanie(
        database=client.Foundtel,
        document_models=[User, Brief, AuditLog]
    )
    print('Connected to MongoDB Atlas — Foundtel database ready')
