"""
OAuth schemas for API requests and responses
"""

from pydantic import BaseModel, Field


class OAuthInitiateResponse(BaseModel):
    """Response for OAuth initiation"""

    authorization_url: str = Field(..., description="URL to redirect user for authorization")
    state: str = Field(..., description="State parameter for CSRF protection")


class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback"""

    access_token: str = Field(..., description="Access token from OAuth provider")
    refresh_token: str = Field(..., description="Refresh token for renewing access")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str = Field(..., description="Granted scopes")


class OAuthCallbackRequest(BaseModel):
    """Request parameters for OAuth callback"""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for validation")


class CalendarIntegrationResponse(BaseModel):
    """Response after creating calendar integration"""

    message: str = Field(..., description="Success message")
    integration_id: str = Field(..., description="ID of created integration")
    provider: str = Field(..., description="Calendar provider name")
    status: str = Field(..., description="Integration status")
