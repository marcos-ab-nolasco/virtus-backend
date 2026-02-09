from uuid import UUID

from pydantic import BaseModel

from src.schemas.user import UserRead
from src.schemas.user_preferences import UserPreferencesResponse
from src.schemas.user_profile import UserProfileResponse
from src.schemas.chat import ConversationRead, MessageRead


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


class AdminConversationList(BaseModel):
    """Schema for listing conversations for a user in the admin panel."""

    conversations: list[ConversationRead]
    total: int
    limit: int
    offset: int


class AdminMessageList(BaseModel):
    """Schema for listing messages for a conversation in the admin panel."""

    messages: list[MessageRead]
    total: int
    limit: int
    offset: int
