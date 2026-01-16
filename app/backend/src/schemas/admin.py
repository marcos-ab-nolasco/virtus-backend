from pydantic import BaseModel

from src.schemas.user import UserRead


class AdminUserList(BaseModel):
    """Schema for listing users in the admin panel."""

    users: list[UserRead]
    total: int
    limit: int
    offset: int
