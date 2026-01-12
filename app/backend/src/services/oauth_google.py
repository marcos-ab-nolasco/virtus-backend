"""
Google OAuth2 Service

Handles OAuth2 flow for Google Calendar integration.
"""

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """OAuth-related errors"""

    pass


class GoogleOAuthService:
    """
    Service for Google OAuth2 authentication

    Implements the authorization code flow for Google APIs.
    """

    # Google OAuth2 endpoints
    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

    # Scopes for Google Calendar
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize OAuth service

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self) -> tuple[str, str]:
        """
        Generate authorization URL for user consent

        Returns:
            Tuple of (authorization_url, state)
            - authorization_url: URL to redirect user to
            - state: Random state for CSRF protection
        """
        # Generate random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }

        authorization_url = f"{self.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

        logger.info(f"Generated authorization URL with state: {state[:8]}...")
        return authorization_url, state

    async def exchange_code_for_tokens(self, code: str, state: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            code: Authorization code from callback
            state: State parameter for validation

        Returns:
            Dictionary with tokens:
            - access_token: Access token
            - refresh_token: Refresh token
            - expires_in: Expiration time in seconds
            - scope: Granted scopes
            - token_type: Token type (Bearer)

        Raises:
            OAuthError: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_ENDPOINT,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Unknown error")
                    error_desc = error_data.get("error_description", "")
                    logger.error(f"Token exchange failed: {error_msg} - {error_desc}")
                    raise OAuthError(f"{error_msg}: {error_desc}")

                tokens: dict[str, Any] = response.json()

                # Validate required fields
                required_fields = ["access_token", "expires_in"]
                if not all(field in tokens for field in required_fields):
                    logger.error(f"Token response missing required fields: {tokens}")
                    raise OAuthError("Invalid token response from Google")

                logger.info("Successfully exchanged code for tokens")
                return tokens

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {e}")
            raise OAuthError(f"Network error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise OAuthError(f"Token exchange failed: {str(e)}") from e

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            Dictionary with new tokens:
            - access_token: New access token
            - expires_in: Expiration time in seconds
            - scope: Granted scopes
            - token_type: Token type (Bearer)

        Raises:
            OAuthError: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_ENDPOINT,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Unknown error")
                    error_desc = error_data.get("error_description", "")
                    logger.error(f"Token refresh failed: {error_msg} - {error_desc}")
                    raise OAuthError(f"{error_msg}: {error_desc}")

                tokens: dict[str, Any] = response.json()
                logger.info("Successfully refreshed access token")
                return tokens

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token refresh: {e}")
            raise OAuthError(f"Network error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise OAuthError(f"Token refresh failed: {str(e)}") from e

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from Google

        Args:
            access_token: Valid access token

        Returns:
            Dictionary with user info:
            - id: Google user ID
            - email: User email
            - verified_email: Whether email is verified
            - name: Full name
            - picture: Profile picture URL

        Raises:
            OAuthError: If user info fetch fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    logger.error(f"User info fetch failed: {response.status_code}")
                    raise OAuthError("Failed to fetch user info")

                user_info: dict[str, Any] = response.json()
                logger.info(f"Fetched user info for: {user_info.get('email')}")
                return user_info

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching user info: {e}")
            raise OAuthError(f"Network error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching user info: {e}")
            raise OAuthError(f"Failed to fetch user info: {str(e)}") from e

    def validate_state(self, received_state: str, expected_state: str) -> None:
        """
        Validate state parameter for CSRF protection

        Args:
            received_state: State from callback
            expected_state: State generated during initiation

        Raises:
            OAuthError: If states don't match
        """
        if received_state != expected_state:
            logger.error(
                f"State mismatch: received={received_state[:8]}..., "
                f"expected={expected_state[:8]}..."
            )
            raise OAuthError("State mismatch - possible CSRF attack")

        logger.debug("State validation passed")
