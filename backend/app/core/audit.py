import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_event(
    session: AsyncSession,
    event_type: str,
    user_id: uuid.UUID | str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    status: str | None = None,
    threat_score: float = 0.0,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict | None = None,
    message: str | None = None,
) -> AuditLog:
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            user_id = None

    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        status=status,
        threat_score=threat_score,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {},
        message=message,
    )
    session.add(entry)
    await session.flush()
    return entry


# Event type constants
class EventType:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKED = "login_locked"
    TOKEN_REFRESH = "token_refresh"
    TASK_SUBMITTED = "task_submitted"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    RAG_RETRIEVAL = "rag_retrieval"
    RAG_QUARANTINE = "rag_quarantine"
    RAG_POISONING_SUSPECTED = "rag_document_poisoning_suspected"
    RAG_POISONED_REJECTED = "rag_poisoned_document_rejected"
    RAG_NO_RESULTS = "rag_no_relevant_results"
    RAG_INDIRECT_INJECTION = "rag_indirect_injection"
    KNOWLEDGE_INGESTED = "knowledge_ingested"
    KNOWLEDGE_DELETED = "knowledge_deleted"
    PROMPT_INJECTION_BLOCKED = "prompt_injection_blocked"
    JAILBREAK_BLOCKED = "jailbreak_blocked"
    CONSTITUTIONAL_VIOLATION = "constitutional_violation"
    PII_DETECTED = "pii_detected"
    RATE_LIMITED = "rate_limited"
    CLEARANCE_DENIED = "clearance_denied"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
