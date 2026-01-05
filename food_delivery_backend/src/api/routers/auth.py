from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.security import create_access_token, hash_password, verify_password
from src.db.models import User
from src.db.session import get_db
from src.schemas import LoginRequest, TokenResponse, UserCreateRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Supports roles: customer, restaurant, delivery.",
)
def register_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Register a user with email/password and role."""
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower().strip(),
        full_name=payload.full_name.strip(),
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email/password. Returns a JWT bearer token.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    user = db.execute(select(User).where(User.email == payload.email.lower().strip())).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), role=str(user.role.value))
    return TokenResponse(access_token=token)
