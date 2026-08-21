from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class ClientOut(BaseModel):
    id: UUID
    tenant_id: UUID
    full_name: str
    phone: str | None
    email: str | None
    created_at: datetime
