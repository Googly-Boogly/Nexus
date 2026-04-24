import uuid
from datetime import datetime
from pydantic import BaseModel, field_serializer


class TaskSubmit(BaseModel):
    agent_type: str
    priority: str = "medium"
    input_text: str
    preferred_provider: str | None = None


class TaskOut(BaseModel):
    id: uuid.UUID

    @field_serializer("id")
    def serialize_id(self, v: uuid.UUID) -> str:
        return str(v)
    agent_type: str
    priority: str
    status: str
    input_text: str
    result: str | None = None
    error_message: str | None = None
    llm_provider: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    rag_chunks_retrieved: int = 0
    rag_sources: list = []
    approval_required: bool = False
    duration_ms: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskEvent(BaseModel):
    event: str
    data: dict
    timestamp: str
