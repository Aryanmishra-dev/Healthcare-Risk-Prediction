from typing import List

from pydantic import BaseModel

from backend.app.schemas.user import UserResponse


class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
