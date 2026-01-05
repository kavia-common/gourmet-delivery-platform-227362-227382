from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from src.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return _pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """Create a JWT access token for a user."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    )
    payload: Dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token; raises jwt exceptions if invalid/expired."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
