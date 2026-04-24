#!/usr/bin/env python3
"""Seed database with demo users and 60 sample tasks."""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.task import Task
from app.models.audit import AuditLog
from app.database import Base


DEMO_USERS = [
    {"username": "admin", "email": "admin@nexus.demo", "password": "Admin123!", "role": "admin", "clearance": "confidential"},
    {"username": "operator", "email": "operator@nexus.demo", "password": "Operator123!", "role": "operator", "clearance": "internal"},
    {"username": "viewer", "email": "viewer@nexus.demo", "password": "Viewer123!", "role": "viewer", "clearance": "public"},
]

AGENT_TYPES = ["incident_response", "infrastructure_provisioning", "compliance_scan"]
PRIORITIES = ["low", "medium", "high", "critical"]
STATUSES = ["completed", "completed", "completed", "failed", "queued"]
SAMPLE_INPUTS = [
    "CPU at 96% on web-server-01. Investigate and remediate.",
    "Payment service returning 503. ~4000 customers affected.",
    "Provision new application server for payments team.",
    "Deploy user-service v2.4.1 to production ECS cluster.",
    "Run SOC2 Type II readiness assessment on production.",
    "Audit all IAM users in production account.",
    "Check patch compliance for all production hosts.",
    "Database replica lag at 45 seconds and growing.",
    "Suspicious outbound traffic from db-server-02.",
    "Scale data processing cluster from 5 to 12 nodes.",
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        # Create users
        users = []
        for u in DEMO_USERS:
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                data_clearance=u["clearance"],
            )
            session.add(user)
            users.append(user)
        await session.flush()

        # Create 60 tasks
        for i in range(60):
            user = random.choice(users)
            agent = random.choice(AGENT_TYPES)
            priority = random.choice(PRIORITIES)
            status = random.choice(STATUSES)
            input_text = random.choice(SAMPLE_INPUTS)

            task = Task(
                user_id=user.id,
                agent_type=agent,
                priority=priority,
                status=status,
                input_text=input_text,
                result="Task completed successfully." if status == "completed" else None,
                tokens_used=random.randint(500, 3000),
                cost_usd=round(random.uniform(0.001, 0.05), 4),
                llm_provider=random.choice(["anthropic", "openai", "demo"]),
                rag_chunks_retrieved=random.randint(0, 8),
                duration_ms=random.randint(500, 8000),
            )
            session.add(task)

        await session.commit()

    await engine.dispose()

    print("\n╔══════════════════════════════════════════╗")
    print("║         NEXUS Demo Credentials           ║")
    print("╠══════════════════════════════════════════╣")
    for u in DEMO_USERS:
        print(f"║  {u['role']:<10} {u['username']:<12} {u['password']:<14}  ║")
    print("╚══════════════════════════════════════════╝")
    print("\n✓ Created 3 users and 60 sample tasks\n")


if __name__ == "__main__":
    asyncio.run(seed())
