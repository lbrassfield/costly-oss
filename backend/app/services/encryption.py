from fastapi import HTTPException
from cryptography.fernet import Fernet

from app.config import settings

fernet = Fernet(settings.encryption_key.encode()) if settings.encryption_key else None


def encrypt_value(value: str) -> str:
    if not fernet:
        raise HTTPException(500, "ENCRYPTION_KEY not configured")
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    if not fernet:
        raise HTTPException(500, "ENCRYPTION_KEY not configured")
    return fernet.decrypt(value.encode()).decode()
