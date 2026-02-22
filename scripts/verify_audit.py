import asyncio
import os
import json
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document, Indexed
from pydantic import Field
from typing import Optional, List

# Import our new modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from founder_agent.db.models import User, Brief, AuditLog
from founder_agent.db.crud import create_user, get_user, get_all_active_users, log_event
from founder_agent.db.security import encrypt_token, decrypt_token
from founder_agent.db.connection import connect_db

async def verify_security_posture():
    print("--- 🛡️ VERIFYING SECURITY POSTURE ---")
    
    # 1. Test Encryption / Decryption
    test_secret = "sk_test_51MzS4HDSK92jK"
    encrypted = encrypt_token(test_secret)
    decrypted = decrypt_token(encrypted)
    
    if encrypted == test_secret:
        print("❌ CRITICAL: Encryption failed! Token stored in plaintext.")
        return False
    
    if decrypted != test_secret:
        print("❌ ERROR: Decryption failed! Data corruption risk.")
        return False
    
    print("✅ Encryption/Decryption logic verified.")
    
    # 2. Test MongoDB Model Integrity (Indexes)
    await connect_db()
    
    # Check if we can insert a duplicate user (should fail due to unique index)
    test_email = f"audit_test_{os.urandom(4).hex()}@example.com"
    await create_user(email=test_email, plan='solo')
    print(f"✅ User created: {test_email}")
    
    try:
        from founder_agent.db.models import User
        # This should fail if the unique index on email is active
        user_duplicate = User(email=test_email, plan='solo')
        await user_duplicate.insert()
        print("❌ CRITICAL: Unique index on users.email is MISSING!")
        return False
    except Exception as e:
        print(f"✅ Unique index verified (Duplicate prevented): {type(e).__name__}")

    # 3. Test Async Batching (CRUD)
    print("--- 📊 VERIFYING BATCHED PROCESSING ---")
    count = 0
    async for user in get_all_active_users():
        count += 1
        if not user.email:
            print("❌ ERROR: User object returned without email.")
            return False
    print(f"✅ Successfully streamed {count} active users via AsyncGenerator.")

    # 4. Test Audit Logging
    await log_event(test_email, "audit_check", "success", "Security audit passed.")
    user_audit = await AuditLog.find_one(AuditLog.user_email == test_email)
    if not user_audit:
        print("❌ ERROR: Audit log not persisted.")
        return False
    print("✅ Audit log persistence verified.")

    print("\n✅ ALL SECURITY AND INTEGRITY CHECKS PASSED.")
    return True

if __name__ == "__main__":
    # Ensure ENCRYPTION_KEY is set for the test
    if not os.getenv("ENCRYPTION_KEY"):
        os.environ["ENCRYPTION_KEY"] = "foundtel-dev-audit-key-32-chars-x!"
        print("⚠️ Using temporary dev ENCRYPTION_KEY for audit.")
        
    asyncio.run(verify_security_posture())
