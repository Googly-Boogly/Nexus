import uuid
from datetime import datetime
from pydantic import BaseModel, field_serializer


class ApprovalOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID | None = None
    requested_by: uuid.UUID
    reviewed_by: uuid.UUID | None = None
    agent_type: str
    priority: str
    input_preview: str | None = None
    status: str
    review_notes: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "task_id", "requested_by", "reviewed_by")
    def serialize_uuid(self, v: uuid.UUID | None) -> str | None:
        return str(v) if v is not None else None


class ApprovalReview(BaseModel):
    action: str  # "approve" | "deny"
    notes: str | None = None
