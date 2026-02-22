import asyncio
from founder_agent.db.connection import connect_db
from founder_agent.db.models import AuditLog

async def check_logs():
    await connect_db()
    logs = await AuditLog.find_all().to_list()
    for log in logs:
        print(f"[{log.created_at}] {log.event_type} - {log.status} - {log.message}")

if __name__ == "__main__":
    asyncio.run(check_logs())
