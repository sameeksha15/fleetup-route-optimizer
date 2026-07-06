"""Auth request/response schemas with server-side validation."""

from __future__ import annotations

import re

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

PASSWORD_MIN = 8
PASSWORD_MAX = 72  # bcrypt's hard limit (bytes)


def normalize_email(value: str) -> str:
    """Validate address syntax (no DNS lookups) and lower-case it for storage."""
    try:
        result = validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError("Enter a valid email address.") from exc
    return result.normalized.lower()


def validate_password(value: str) -> str:
    if len(value) < PASSWORD_MIN:
        raise ValueError("Password must be at least 8 characters.")
    if len(value.encode("utf-8")) > PASSWORD_MAX:
        raise ValueError("Password must be at most 72 characters.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must include at least one letter and one number.")
    return value


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    company_name: str = Field(min_length=1, max_length=120)
    email: str
    password: str

    @field_validator("full_name", "company_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return validate_password(v)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    organization: OrganizationOut
