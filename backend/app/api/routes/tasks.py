import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.tasks import TaskOut, TaskSubmit

router = APIRouter(prefix="/tasks", tags=["tasks"])

HIGH_PRIORITY_REQUIRES_APPROVAL = {"high", "critical"}


@router.post("", response_model=TaskOut)
async def submit_task(
    body: TaskSubmit,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if body.agent_type not in ("incident_response", "infrastructure_provisioning", "compliance_scan"):
        raise HTTPException(status_code=422, detail="Invalid agent_type")

    approval_required = body.priority in HIGH_PRIORITY_REQUIRES_APPROVAL
    initial_status = "awaiting_approval" if approval_required else "queued"

    task = Task(
        user_id=user.id,
        agent_type=body.agent_type,
        priority=body.priority,
        status=initial_status,
        input_text=body.input_text,
        approval_required=approval_required,
    )
    session.add(task)
    await session.flush()
    task_id = str(task.id)

    if approval_required:
        from app.models.approval import Approval
        approval = Approval(
            task_id=task.id,
            requested_by=user.id,
            agent_type=body.agent_type,
            priority=body.priority,
            input_preview=body.input_text[:200],
        )
        session.add(approval)
    else:
        if settings.DEMO_MODE:
            task.celery_task_id = f"demo-{task_id}"
            task.status = "running"
        else:
            from app.workers.task_worker import execute_agent_task
            celery_result = execute_agent_task.delay(
                task_id=task_id,
                user_id=str(user.id),
                user_role=user.role,
                user_clearance=user.data_clearance,
                agent_type=body.agent_type,
                priority=body.priority,
                input_text=body.input_text,
                preferred_provider=body.preferred_provider,
            )
            task.celery_task_id = celery_result.id
            task.status = "running"

    await session.commit()
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Task).where(Task.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if str(task.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if user.role == "admin":
        result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(100))
    else:
        result = await session.execute(
            select(Task).where(Task.user_id == user.id).order_by(Task.created_at.desc()).limit(100)
        )
    return list(result.scalars().all())


@router.websocket("/ws/{task_id}")
async def task_stream(
    websocket: WebSocket,
    task_id: str,
):
    token = websocket.query_params.get("token", "")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        import redis.asyncio as aioredis
        from app.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        channel = f"task:{task_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        try:
            deadline = 300
            elapsed = 0
            while elapsed < deadline:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    await websocket.send_text(data)
                    parsed = json.loads(data)
                    if parsed.get("event") in ("completed", "failed"):
                        break
                elapsed += 1
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
