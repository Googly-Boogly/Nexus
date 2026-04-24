import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user, require_admin
from app.config import settings
from app.core.audit import EventType, log_event
from app.database import get_db
from app.models.approval import Approval
from app.models.task import Task
from app.models.user import User
from app.schemas.approvals import ApprovalOut, ApprovalReview

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if user.role != "admin":
        stmt = stmt.where(Approval.requested_by == user.id)
    if status:
        stmt = stmt.where(Approval.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{approval_id}", response_model=ApprovalOut)
async def get_approval(
    approval_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Approval).where(Approval.id == uuid.UUID(approval_id))
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/{approval_id}/review", response_model=ApprovalOut)
async def review_approval(
    approval_id: str,
    body: ApprovalReview,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    if body.action not in ("approve", "deny"):
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'deny'")

    result = await session.execute(
        select(Approval).where(Approval.id == uuid.UUID(approval_id))
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval already reviewed")

    approval.status = "approved" if body.action == "approve" else "denied"
    approval.reviewed_by = admin.id
    approval.review_notes = body.notes
    approval.reviewed_at = datetime.now(timezone.utc)

    event = EventType.APPROVAL_GRANTED if body.action == "approve" else EventType.APPROVAL_DENIED
    await log_event(session, event, user_id=admin.id, resource_id=approval_id,
                    details={"notes": body.notes})

    if body.action == "approve" and approval.task_id:
        task_result = await session.execute(
            select(Task).where(Task.id == approval.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Associated task not found")

        requester_result = await session.execute(
            select(User).where(User.id == approval.requested_by)
        )
        requester = requester_result.scalar_one_or_none()
        if not requester:
            raise HTTPException(status_code=404, detail="Task requester not found")

        if settings.DEMO_MODE:
            task.status = "completed"
            task.result = f"[DEMO] Approved {task.agent_type} task executed."
        else:
            from app.workers.task_worker import execute_agent_task
            celery = execute_agent_task.delay(
                task_id=str(task.id),
                user_id=str(requester.id),
                user_role=requester.role,
                user_clearance=requester.data_clearance,
                agent_type=task.agent_type,
                priority=task.priority,
                input_text=task.input_text,
                approval_id=str(approval.id),
            )
            task.celery_task_id = celery.id
            task.status = "running"

    await session.commit()
    return approval
