"""
OAuth API endpoints

Handles OAuth2 flow for external service integrations.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.dependencies import get_current_user
from src.core.encryption import encrypt_token
from src.db.models.calendar_integration import (
    CalendarIntegration,
    CalendarProvider,
    IntegrationStatus,
)
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.oauth import CalendarIntegrationResponse, OAuthInitiateResponse
from src.services.oauth_google import GoogleOAuthService, OAuthError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["OAuth"])

# In-memory state storage (for development)
# In production, use Redis or database
oauth_states: dict[str, dict] = {}


def get_google_oauth_service() -> GoogleOAuthService:
    """Get Google OAuth service with configuration"""
    settings = get_settings()

    return GoogleOAuthService(
        client_id=settings.GOOGLE_CLIENT_ID or "",
        client_secret=settings.GOOGLE_CLIENT_SECRET or "",
        redirect_uri=settings.GOOGLE_REDIRECT_URI
        or "http://localhost:8000/api/v1/auth/google/callback",
    )


@router.get("/google", response_model=OAuthInitiateResponse)
async def initiate_google_oauth(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> OAuthInitiateResponse:
    """
    Initiate Google OAuth flow

    Returns authorization URL for user to grant permissions.
    State parameter is stored temporarily for validation.
    """
    try:
        authorization_url, state = oauth_service.get_authorization_url()

        # Store state temporarily (expires in 10 minutes)
        # In production, use Redis with TTL for automatic expiration
        oauth_states.clear()  # Simplified: clear all old states
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "provider": "google",
        }

        logger.info(f"Initiated OAuth flow with state: {state[:8]}...")
        return OAuthInitiateResponse(
            authorization_url=authorization_url,
            state=state,
        )

    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow",
        ) from e


@router.get("/google/callback", response_model=CalendarIntegrationResponse)
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for validation"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> CalendarIntegrationResponse:
    """
    Handle Google OAuth callback

    Exchanges authorization code for tokens and creates calendar integration.
    """
    try:
        # Validate state
        if state not in oauth_states:
            logger.error(f"Invalid or expired state: {state[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )

        # Remove used state
        oauth_states.pop(state, None)

        # Exchange code for tokens
        logger.info(f"Exchanging code for tokens for user: {current_user.id}")
        tokens = await oauth_service.exchange_code_for_tokens(code, state)

        # Get user info from Google
        user_info = await oauth_service.get_user_info(tokens["access_token"])
        logger.info(f"Received user info for: {user_info.get('email')}")

        # Encrypt tokens before storing
        encrypted_access_token = encrypt_token(tokens["access_token"])
        encrypted_refresh_token = encrypt_token(tokens.get("refresh_token", ""))

        # Calculate token expiry
        expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])

        # Parse scopes from string to list
        scopes_list = tokens.get("scope", "").split() if tokens.get("scope") else []

        # Create or update calendar integration
        integration = CalendarIntegration(
            user_id=current_user.id,
            provider=CalendarProvider.GOOGLE_CALENDAR,
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_expires_at=expires_at,
            scopes=scopes_list,
            status=IntegrationStatus.ACTIVE,
        )

        db.add(integration)
        await db.commit()
        await db.refresh(integration)

        logger.info(f"Created calendar integration {integration.id} for user {current_user.id}")

        return CalendarIntegrationResponse(
            message="Successfully connected Google Calendar",
            integration_id=str(integration.id),
            provider=integration.provider.value,
            status=integration.status.value,
        )

    except HTTPException:
        # Re-raise HTTPException without catching (FastAPI handles it)
        raise
    except OAuthError as e:
        logger.error(f"OAuth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth flow",
        ) from e
