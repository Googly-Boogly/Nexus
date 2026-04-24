import uuid
from datetime import datetime
from pydantic import BaseModel, field_serializer


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    event_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    status: str | None = None
    threat_score: float = 0.0
    ip_address: str | None = None
    details: dict = {}
    message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "user_id")
    def serialize_uuid(self, v: uuid.UUID | None) -> str | None:
        return str(v) if v is not None else None


class AuditFilter(BaseModel):
    event_type: str | None = None
    user_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 50
    offset: int = 0
