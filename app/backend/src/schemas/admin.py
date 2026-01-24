from uuid import UUID

from pydantic import BaseModel

from src.schemas.user import UserRead
from src.schemas.user_preferences import UserPreferencesResponse
from src.schemas.user_profile import UserProfileResponse


class AdminUserList(BaseModel):
    """Schema for listing users in the admin panel."""

    users: list[UserRead]
    total: int
    limit: int
    offset: int


class AdminUserOnboardingResponse(BaseModel):
    """Schema for admin access to user onboarding data."""

    user_id: UUID
    profile: UserProfileResponse
    preferences: UserPreferencesResponse
