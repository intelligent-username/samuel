import base64
import hashlib

from cryptography.fernet import Fernet as _Fernet

from app.config import settings


def _derive_key(secret: str) -> bytes:
    """Derive a valid 44-char base64 Fernet key from an arbitrary secret."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_cipher = _Fernet(_derive_key(settings.encryption_key))


def encrypt(plaintext: str) -> str:
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _cipher.decrypt(ciphertext.encode()).decode()