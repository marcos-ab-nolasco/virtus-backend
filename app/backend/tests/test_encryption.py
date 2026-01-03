"""Tests for token encryption utilities."""

import pytest
from cryptography.fernet import InvalidToken

from src.core.encryption import decrypt_token, encrypt_token


def test_encrypt_token_returns_different_value():
    """Test that encrypt_token returns a different value than the input."""
    token = "my_secret_oauth_token_12345"
    encrypted = encrypt_token(token)

    assert encrypted != token
    assert len(encrypted) > 0
    assert isinstance(encrypted, str)


def test_encrypt_decrypt_roundtrip():
    """Test that encrypting and then decrypting returns the original value."""
    original_token = "test_access_token_abc123xyz"

    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == original_token


def test_encrypt_same_token_twice_produces_different_ciphertext():
    """Test that encrypting the same token twice produces different results (due to IV)."""
    token = "same_token_value"

    encrypted1 = encrypt_token(token)
    encrypted2 = encrypt_token(token)

    # Ciphertexts should be different (Fernet uses random IV)
    assert encrypted1 != encrypted2

    # But both should decrypt to the same value
    assert decrypt_token(encrypted1) == token
    assert decrypt_token(encrypted2) == token


def test_decrypt_invalid_token_raises_error():
    """Test that decrypting an invalid token raises an error."""
    invalid_encrypted = "this_is_not_a_valid_fernet_token"

    with pytest.raises(InvalidToken):
        decrypt_token(invalid_encrypted)


def test_encrypt_empty_string():
    """Test encrypting an empty string."""
    token = ""
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == token


def test_encrypt_long_token():
    """Test encrypting a long token (simulating JWT or OAuth token)."""
    # Simulate a long JWT-like token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." * 10  # Long token
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == token
    assert len(encrypted) > len(token)  # Encrypted should be longer due to encoding


def test_decrypt_tampered_token_raises_error():
    """Test that tampering with an encrypted token raises an error."""
    token = "original_token"
    encrypted = encrypt_token(token)

    # Tamper with the encrypted token (change a character)
    if len(encrypted) > 10:
        tampered = encrypted[:10] + "X" + encrypted[11:]

        with pytest.raises(InvalidToken):
            decrypt_token(tampered)
