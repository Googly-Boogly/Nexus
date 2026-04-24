from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditFilter, AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

    if user.role != "admin":
        stmt = stmt.where(AuditLog.user_id == user.id)

    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{log_id}", response_model=AuditLogOut)
async def get_audit_log(
    log_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    import uuid
    result = await session.execute(
        select(AuditLog).where(AuditLog.id == uuid.UUID(log_id))
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    if str(log.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return log
