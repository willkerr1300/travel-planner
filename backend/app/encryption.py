from cryptography.fernet import Fernet
from app.config import settings

_fernet = Fernet(settings.encryption_key.encode())


def encrypt(value: str | None) -> str | None:
    """Encrypt a plain-text string. Returns None if value is None or empty."""
    if not value:
        return None
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    """Decrypt a Fernet-encrypted string. Returns None if value is None or empty."""
    if not value:
        return None
    return _fernet.decrypt(value.encode()).decode()
