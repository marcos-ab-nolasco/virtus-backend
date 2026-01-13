"""
Tests for Google OAuth2 Integration (Issue 2.1)

Following TDD approach for OAuth flow.
"""

from unittest.mock import patch

import pytest
from httpx import Response

from src.schemas.oauth import OAuthCallbackResponse, OAuthInitiateResponse
from src.services.oauth_google import GoogleOAuthService, OAuthError


class TestGoogleOAuthService:
    """Test Google OAuth service"""

    def setup_method(self):
        """Setup OAuth service with test credentials"""
        self.service = GoogleOAuthService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/auth/google/callback",
        )

    def test_service_initialization(self):
        """Service should initialize with credentials"""
        assert self.service.client_id == "test-client-id"
        assert self.service.client_secret == "test-client-secret"
        assert self.service.redirect_uri == "http://localhost:8000/auth/google/callback"

    def test_get_authorization_url(self):
        """Should generate authorization URL with state"""
        url, state = self.service.get_authorization_url()

        assert isinstance(url, str)
        assert isinstance(state, str)
        assert "https://accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=test-client-id" in url
        assert f"state={state}" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert len(state) >= 32  # State should be random and long enough

    def test_authorization_url_includes_calendar_scope(self):
        """Authorization URL should request calendar scope"""
        url, state = self.service.get_authorization_url()

        assert "scope=" in url
        # Should include calendar read scope
        assert "calendar.readonly" in url or "calendar" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self):
        """Should exchange authorization code for tokens"""
        mock_response = {
            "access_token": "ya29.test-access-token",
            "refresh_token": "1//test-refresh-token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "token_type": "Bearer",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_response,
            )

            tokens = await self.service.exchange_code_for_tokens(
                code="test-auth-code",
                state="test-state",
            )

            assert tokens["access_token"] == "ya29.test-access-token"
            assert tokens["refresh_token"] == "1//test-refresh-token"
            assert tokens["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_code_raises_error(self):
        """Should raise error for invalid authorization code"""
        mock_response = {"error": "invalid_grant", "error_description": "Invalid code"}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=400,
                json=mock_response,
            )

            with pytest.raises(OAuthError, match="invalid_grant"):
                await self.service.exchange_code_for_tokens(
                    code="invalid-code",
                    state="test-state",
                )

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self):
        """Should refresh access token using refresh token"""
        mock_response = {
            "access_token": "ya29.new-access-token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "token_type": "Bearer",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json=mock_response,
            )

            tokens = await self.service.refresh_access_token("1//test-refresh-token")

            assert tokens["access_token"] == "ya29.new-access-token"
            assert tokens["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_raises_error(self):
        """Should raise error for invalid refresh token"""
        mock_response = {
            "error": "invalid_grant",
            "error_description": "Token has been expired or revoked.",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=400,
                json=mock_response,
            )

            with pytest.raises(OAuthError, match="invalid_grant"):
                await self.service.refresh_access_token("invalid-refresh-token")

    def test_validate_state_success(self):
        """Should validate state parameter"""
        state = "valid-state-12345"
        # Should not raise
        self.service.validate_state(state, state)

    def test_validate_state_mismatch_raises_error(self):
        """Should raise error on state mismatch"""
        with pytest.raises(OAuthError, match="State mismatch"):
            self.service.validate_state("state-1", "state-2")

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Should fetch user info from Google"""
        mock_response = {
            "id": "12345",
            "email": "user@example.com",
            "verified_email": True,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = Response(
                status_code=200,
                json=mock_response,
            )

            user_info = await self.service.get_user_info("ya29.test-access-token")

            assert user_info["email"] == "user@example.com"
            assert user_info["id"] == "12345"
            assert user_info["verified_email"] is True


class TestOAuthCallbackResponse:
    """Test OAuth callback response schema"""

    def test_create_callback_response(self):
        """Should create callback response"""
        response = OAuthCallbackResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
            scope="calendar.readonly",
        )

        assert response.access_token == "token"
        assert response.refresh_token == "refresh"
        assert response.expires_in == 3600


class TestOAuthInitiateResponse:
    """Test OAuth initiate response schema"""

    def test_create_initiate_response(self):
        """Should create initiate response"""
        response = OAuthInitiateResponse(
            authorization_url="https://accounts.google.com/...",
            state="random-state",
        )

        assert "https://accounts.google.com" in response.authorization_url
        assert response.state == "random-state"


class TestOAuthEndpoints:
    """Test OAuth API endpoints"""

    @pytest.mark.asyncio
    async def test_initiate_oauth_returns_redirect_url(self, client):
        """GET /auth/google should return authorization URL"""
        response = await client.get("/api/v1/auth/google")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_oauth_callback_success(self, client, test_user, auth_headers):
        """GET /auth/google/callback should exchange code for tokens"""
        # Mock the OAuth service
        with patch(
            "src.services.oauth_google.GoogleOAuthService.exchange_code_for_tokens"
        ) as mock_exchange:
            mock_exchange.return_value = {
                "access_token": "ya29.test-token",
                "refresh_token": "1//test-refresh",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.readonly",
            }

            with patch(
                "src.services.oauth_google.GoogleOAuthService.get_user_info"
            ) as mock_user_info:
                mock_user_info.return_value = {
                    "email": test_user.email,
                    "id": "google-123",
                }

                # Store state for validation
                with patch("src.api.oauth.oauth_states", {"test-state": {"created_at": "test", "provider": "google"}}):
                    response = await client.get(
                        "/api/v1/auth/google/callback?code=test-code&state=test-state",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "message" in data
                    assert "integration_id" in data

    @pytest.mark.asyncio
    async def test_oauth_callback_missing_code_returns_error(self, client, auth_headers):
        """Callback without code should return error"""
        response = await client.get("/api/v1/auth/google/callback", headers=auth_headers)

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_state_returns_error(self, client, auth_headers):
        """Callback with invalid state should return error"""
        # State not in oauth_states dict (invalid/expired)
        with patch("src.api.oauth.oauth_states", {}):
            response = await client.get(
                "/api/v1/auth/google/callback?code=test&state=invalid",
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "state" in data["detail"].lower()


class TestOAuthStateManagement:
    """Test OAuth state management and security"""

    def test_state_is_random_and_unique(self):
        """Each authorization should generate unique state"""
        service = GoogleOAuthService(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost/callback",
        )

        url1, state1 = service.get_authorization_url()
        url2, state2 = service.get_authorization_url()

        assert state1 != state2
        assert len(state1) >= 32
        assert len(state2) >= 32

    def test_state_storage_and_retrieval(self):
        """Should store and retrieve state for validation"""
        service = GoogleOAuthService(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost/callback",
        )

        url, state = service.get_authorization_url()

        # State should be validatable
        # In real implementation, this would check against stored state
        assert service.validate_state(state, state) is None


class TestOAuthTokenEncryption:
    """Test token encryption for storage"""

    @pytest.mark.asyncio
    async def test_tokens_are_encrypted_before_storage(self, client, test_user, auth_headers):
        """Tokens should be encrypted before storing in database"""
        with patch(
            "src.services.oauth_google.GoogleOAuthService.exchange_code_for_tokens"
        ) as mock_exchange:
            mock_exchange.return_value = {
                "access_token": "plaintext-access-token",
                "refresh_token": "plaintext-refresh-token",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.readonly",
            }

            with patch(
                "src.services.oauth_google.GoogleOAuthService.get_user_info"
            ) as mock_user_info:
                mock_user_info.return_value = {
                    "email": test_user.email,
                    "id": "google-123",
                }

                with patch("src.api.oauth.encrypt_token") as mock_encrypt:
                    mock_encrypt.side_effect = lambda x: f"encrypted_{x}"

                    # Store state for validation
                    with patch("src.api.oauth.oauth_states", {"test-state": {"created_at": "test", "provider": "google"}}):
                        response = await client.get(
                            "/api/v1/auth/google/callback?code=test-code&state=test-state",
                            headers=auth_headers,
                        )

                        assert response.status_code == 200
                        # Verify encrypt_token was called twice (access + refresh)
                        assert mock_encrypt.call_count == 2


class TestOAuthErrorHandling:
    """Test OAuth error scenarios"""

    @pytest.mark.asyncio
    async def test_network_error_during_token_exchange(self):
        """Should handle network errors gracefully"""
        service = GoogleOAuthService(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost/callback",
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(OAuthError):
                await service.exchange_code_for_tokens("code", "state")

    @pytest.mark.asyncio
    async def test_malformed_response_from_google(self):
        """Should handle malformed API responses"""
        service = GoogleOAuthService(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost/callback",
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200,
                json={"unexpected": "format"},  # Missing required fields
            )

            with pytest.raises(OAuthError):
                await service.exchange_code_for_tokens("code", "state")
