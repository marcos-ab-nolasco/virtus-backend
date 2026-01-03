"""Token encryption utilities for securing sensitive data.

Uses Fernet symmetric encryption to encrypt/decrypt OAuth tokens and other sensitive data
before storing in the database. Fernet uses AES-128 in CBC mode with PKCS7 padding.

The encryption key must be a 32 URL-safe base64-encoded bytes, generated with:
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
"""

from cryptography.fernet import Fernet

from src.core.config import get_settings


def get_cipher() -> Fernet:
    """Get Fernet cipher instance from settings.

    Returns:
        Fernet: Configured cipher instance using the ENCRYPTION_KEY from settings.

    Raises:
        ValueError: If ENCRYPTION_KEY is not properly formatted.
    """
    settings = get_settings()
    key = settings.ENCRYPTION_KEY.get_secret_value().encode()
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage.

    Args:
        token: The plaintext token to encrypt (e.g., OAuth access token).

    Returns:
        str: The encrypted token as a URL-safe base64-encoded string.

    Example:
        >>> access_token = "ya29.a0AfH6SMB..."
        >>> encrypted = encrypt_token(access_token)
        >>> # Store encrypted in database
    """
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token.

    Args:
        encrypted_token: The encrypted token string from database.

    Returns:
        str: The original plaintext token.

    Raises:
        cryptography.fernet.InvalidToken: If the token is invalid or tampered with.

    Example:
        >>> encrypted = "gAAAAABf..."  # From database
        >>> access_token = decrypt_token(encrypted)
        >>> # Use access_token for API calls
    """
    cipher = get_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_token.encode())
    return decrypted_bytes.decode()
