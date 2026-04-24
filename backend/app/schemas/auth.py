import uuid

from pydantic import BaseModel, EmailStr, field_serializer


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str
    data_clearance: str
    is_active: bool

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v: uuid.UUID) -> str:
        return str(v)


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "viewer"
    data_clearance: str = "internal"


class UserUpdate(BaseModel):
    role: str | None = None
    data_clearance: str | None = None
    is_active: bool | None = None
