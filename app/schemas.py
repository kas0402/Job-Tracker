from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ApplicationCreate(BaseModel):
    company: str
    role: str
    link: str | None = None
    salary: int | None = None
    status: str = "saved"
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    link: str | None = None
    salary: int | None = None
    status: str | None = None
    notes: str | None = None


class ApplicationRead(ApplicationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    old_status: str | None
    new_status: str
    changed_at: datetime


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]