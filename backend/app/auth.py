from fastapi import Header, HTTPException, status
from app.config import settings


def require_internal_key(x_api_key: str = Header(...)) -> str:
    """
    FastAPI dependency — verifies the shared internal API key.
    The Next.js backend injects this header on every server-to-server call.
    FastAPI should never be directly exposed to the public internet.
    """
    if x_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key


def get_current_user_email(x_user_email: str = Header(...)) -> str:
    """
    FastAPI dependency — extracts the authenticated user's email from the
    header injected by the Next.js API route after verifying the session.
    """
    if not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user email header",
        )
    return x_user_email
