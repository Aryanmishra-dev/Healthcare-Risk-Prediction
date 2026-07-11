from typing import Any
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class SessionResponse(BaseModel):
    id: str
    user_agent: str | None
    ip_address: str | None
    created_at: Any
    expires_at: Any
    is_revoked: bool
