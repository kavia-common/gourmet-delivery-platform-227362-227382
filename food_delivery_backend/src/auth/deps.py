from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.security import decode_access_token
from src.db.models import User, UserRole
from src.db.session import get_db

_security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


# PUBLIC_INTERFACE
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    """Return the current authenticated user (raises 401 if missing/invalid token)."""
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise _unauthorized("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token payload")

    user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


# PUBLIC_INTERFACE
def require_role(required_role: UserRole):
    """Factory for a dependency that enforces a specific user role."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _dep
