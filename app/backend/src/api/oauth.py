"""
OAuth API endpoints

Handles OAuth2 flow for external service integrations.
"""

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
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
from src.schemas.oauth import CalendarIntegrationCreateResponse, OAuthInitiateResponse
from src.services.oauth_google import GoogleOAuthService, OAuthError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["OAuth"])

# In-memory state storage (for development)
# In production, use Redis or database
oauth_states: dict[str, dict] = {}


def _build_redirect_url(base_url: str, params: dict[str, str]) -> str:
    """Append query params to a base URL, preserving existing params."""
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query.update({key: value for key, value in params.items() if value})
    updated_query = urlencode(query)
    return urlunparse(parsed._replace(query=updated_query))


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
    current_user: User = Depends(get_current_user),
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
        state_payload: dict[str, str | datetime] = {
            "created_at": datetime.now(UTC),
            "provider": "google",
        }
        state_payload["user_id"] = str(current_user.id)
        oauth_states[state] = state_payload

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


@router.get("/google/callback")
async def google_oauth_callback(
    code: str | None = Query(None, description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for validation"),
    error: str | None = Query(None, description="OAuth error from Google"),
    error_description: str | None = Query(None, description="OAuth error description"),
    db: AsyncSession = Depends(get_db),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> CalendarIntegrationCreateResponse:
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
        state_data = oauth_states.pop(state, None) or {}
        user_id_raw = state_data.get("user_id")
        if not user_id_raw:
            logger.error("OAuth state missing user_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            )

        try:
            user_id = UUID(user_id_raw)
        except (ValueError, TypeError) as e:
            logger.error("OAuth state user_id invalid: %s", user_id_raw)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            ) from e

        # Exchange code for tokens
        if error:
            logger.info(
                "OAuth callback returned error: %s description=%s user_id=%s",
                error,
                error_description,
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code",
            )

        logger.info(f"Exchanging code for tokens for user: {user_id}")
        tokens = await oauth_service.exchange_code_for_tokens(code, state)

        # Get user info from Google
        user_info = await oauth_service.get_user_info(tokens["access_token"])
        logger.info(f"Received user info for: {user_info.get('email')}")

        # Encrypt tokens before storing
        encrypted_access_token = encrypt_token(tokens["access_token"])
        encrypted_refresh_token = encrypt_token(tokens.get("refresh_token", ""))

        # Calculate token expiry
        expires_at = datetime.now(UTC) + timedelta(seconds=tokens["expires_in"])

        # Parse scopes from string to list
        scopes_list = tokens.get("scope", "").split() if tokens.get("scope") else []

        # Create or update calendar integration
        integration = CalendarIntegration(
            user_id=user_id,
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

        # logger.info(f"Created calendar integration {integration.id} for user {current_user.id}")

        settings = get_settings()
        if settings.FRONTEND_OAUTH_REDIRECT_URL:
            redirect_url = _build_redirect_url(
                settings.FRONTEND_OAUTH_REDIRECT_URL,
                {
                    "status": "connected",
                    "provider": integration.provider.value.lower(),
                    "integration_id": str(integration.id),
                },
            )
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

        return CalendarIntegrationCreateResponse(
            message="Successfully connected Google Calendar",
            integration_id=str(integration.id),
            provider=integration.provider.value,
            status=integration.status.value,
        )

    except HTTPException as e:
        settings = get_settings()
        if settings.FRONTEND_OAUTH_REDIRECT_URL:
            reason = "oauth_failed"
            if e.status_code == status.HTTP_400_BAD_REQUEST:
                if e.detail in {"Invalid or expired OAuth state", "Invalid OAuth state"}:
                    reason = "invalid_state"
                elif e.detail == "access_denied":
                    reason = "access_denied"
                elif e.detail == "Failed to complete OAuth flow":
                    reason = "internal_error"
            redirect_url = _build_redirect_url(
                settings.FRONTEND_OAUTH_REDIRECT_URL,
                {
                    "status": "failed",
                    "provider": "google",
                    "reason": reason,
                },
            )
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        raise
    except OAuthError as e:
        logger.error(f"OAuth error: {e}")
        settings = get_settings()
        if settings.FRONTEND_OAUTH_REDIRECT_URL:
            redirect_url = _build_redirect_url(
                settings.FRONTEND_OAUTH_REDIRECT_URL,
                {
                    "status": "failed",
                    "provider": "google",
                    "reason": "oauth_error",
                },
            )
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        settings = get_settings()
        if settings.FRONTEND_OAUTH_REDIRECT_URL:
            redirect_url = _build_redirect_url(
                settings.FRONTEND_OAUTH_REDIRECT_URL,
                {
                    "status": "failed",
                    "provider": "google",
                    "reason": "internal_error",
                },
            )
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth flow",
        ) from e
