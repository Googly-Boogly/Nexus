#!/bin/bash
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding database if needed..."
python - <<'EOF'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from app.core.security import hash_password

DEMO_USERS = [
    {"username": "admin",    "email": "admin@nexus.demo",    "password": "Admin123!",    "role": "admin",    "clearance": "confidential"},
    {"username": "operator", "email": "operator@nexus.demo", "password": "Operator123!", "role": "operator", "clearance": "internal"},
    {"username": "viewer",   "email": "viewer@nexus.demo",   "password": "Viewer123!",   "role": "viewer",   "clearance": "public"},
]

async def seed_if_empty():
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar():
            print("Users already exist — skipping seed.")
            await engine.dispose()
            return
        for u in DEMO_USERS:
            session.add(User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                data_clearance=u["clearance"],
            ))
        await session.commit()
        print("Seeded demo users: admin / operator / viewer")
    await engine.dispose()

asyncio.run(seed_if_empty())
EOF

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
