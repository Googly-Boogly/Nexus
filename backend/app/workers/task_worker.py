import asyncio
import json
from datetime import datetime, timezone

import redis as sync_redis

from app.config import settings
from app.workers.celery_app import celery_app


def publish_event(task_id: str, event_type: str, data: dict) -> None:
    try:
        r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
        payload = json.dumps({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.publish(f"task:{task_id}:events", payload)
    except Exception:
        pass


@celery_app.task(bind=True, name="execute_agent_task")
def execute_agent_task(
    self,
    task_id: str,
    user_id: str,
    user_role: str,
    user_clearance: str,
    agent_type: str,
    priority: str,
    input_text: str,
    preferred_provider: str | None = None,
    approval_id: str | None = None,
) -> dict:
    publish_event(task_id, "started", {
        "agent_type": agent_type,
        "provider": preferred_provider or "auto",
        "rag_enabled": True,
    })

    async def run():
        from app.database import AsyncSessionLocal
        from app.agents.orchestrator import get_agent
        from app.core.audit import EventType, log_event
        from app.models.task import Task
        import uuid
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            try:
                agent = get_agent(agent_type)

                result = await agent.run(
                    task_id=task_id,
                    user_id=user_id,
                    user_role=user_role,
                    user_clearance=user_clearance,
                    input_text=input_text,
                    priority=priority,
                    session=session,
                    preferred_provider=preferred_provider,
                    approval_id=approval_id,
                    publish=lambda evt, data: publish_event(task_id, evt, data),
                )

                task_uuid = uuid.UUID(task_id)
                db_result = await session.execute(select(Task).where(Task.id == task_uuid))
                task = db_result.scalar_one_or_none()
                if task:
                    task.status = result.status
                    task.result = result.output
                    task.error_message = result.error
                    task.tokens_used = result.tokens_used
                    task.cost_usd = result.cost_usd
                    task.llm_provider = result.llm_provider
                    task.rag_chunks_retrieved = len(result.rag_sources)
                    task.rag_sources = result.rag_sources
                    task.duration_ms = result.duration_ms
                await session.commit()

                publish_event(task_id, "completed", {
                    "result_preview": result.output[:200],
                    "duration_ms": result.duration_ms,
                    "tokens_used": result.tokens_used,
                    "cost_usd": result.cost_usd,
                    "llm_provider": result.llm_provider,
                })

                return {"status": result.status, "output": result.output}

            except Exception as e:
                error_msg = str(e)
                publish_event(task_id, "failed", {"error": error_msg, "step_failed": "execution"})
                try:
                    await session.rollback()
                except Exception:
                    pass

                # Use a fresh session so the failure audit + task status always persist
                try:
                    async with AsyncSessionLocal() as fail_session:
                        task_uuid = uuid.UUID(task_id)
                        db_result = await fail_session.execute(select(Task).where(Task.id == task_uuid))
                        task = db_result.scalar_one_or_none()
                        if task:
                            task.status = "failed"
                            task.error_message = error_msg[:500]
                        await log_event(
                            fail_session, EventType.TASK_FAILED,
                            user_id=user_id,
                            resource_type="task",
                            resource_id=task_id,
                            details={"agent_type": agent_type, "error": error_msg[:500]},
                            message=error_msg[:500],
                        )
                        await fail_session.commit()
                except Exception:
                    pass

                raise

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run())
    finally:
        loop.close()
