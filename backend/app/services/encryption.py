import base64
import hashlib

from cryptography.fernet import Fernet as _Fernet

from app.config import settings


def _derive_key(secret: str) -> bytes:
    """Derive a valid Fernet key from an arbitrary-length secret using SHA-256."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


_cipher = _Fernet(_derive_key(settings.encryption_key))


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext using Fernet symmetric encryption.

    Args:
        plaintext: The string to encrypt (e.g., an API key).

    Returns:
        A base64-encoded ciphertext string.
    """
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext back to plaintext.

    Args:
        ciphertext: The base64-encoded encrypted string.

    Returns:
        The original plaintext string.
    """
    return _cipher.decrypt(ciphertext.encode()).decode()
