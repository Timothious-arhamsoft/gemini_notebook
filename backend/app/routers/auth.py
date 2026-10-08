import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_validation import (
    validate_email_address,
    validate_full_name,
    validate_password,
    validate_username,
)
from app.database import get_db
from app.models import Notebook, User

logger = logging.getLogger(__name__)

# Same base as notebooks/sources routers — DB rows and files are separate concerns
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"


router = APIRouter()

pwd_ctx = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

security = HTTPBearer()

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key",
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# ─── JWT Helpers ────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        user_uuid = uuid.UUID(user_id)

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = (
        db.query(User)
        .filter(User.id == user_uuid)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def _duplicate_account_detail(exc: IntegrityError) -> str:
    """Map DB unique violations to clean client messages (no SQL details)."""
    raw = str(getattr(exc, "orig", None) or exc).lower()
    if "username" in raw:
        return "Username already taken."
    if "email" in raw:
        return "Email already registered."
    return "Account already exists."


# ─── Schemas ────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: str
    username: str
    full_name: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return validate_email_address(value)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, value: str) -> str:
        return validate_full_name(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return validate_email_address(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Routes ────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    """Register a new user."""

    if (
        db.query(User)
        .filter(func.lower(User.email) == payload.email)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    if (
        db.query(User)
        .filter(func.lower(User.username) == payload.username)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=pwd_ctx.hash(payload.password),
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_duplicate_account_detail(exc),
        ) from None

    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user and return a JWT."""

    user = (
        db.query(User)
        .filter(func.lower(User.email) == payload.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not pwd_ctx.verify(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user."""

    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the authenticated user (cascade), then remove notebook storage dirs."""
    notebook_ids = [
        row[0]
        for row in db.query(Notebook.id)
        .filter(Notebook.user_id == current_user.id)
        .all()
    ]

    # 1) DB relationships (notebooks → sources/chunks/chat, refresh tokens, user)
    db.delete(current_user)
    db.commit()

    # 2) Physical storage — cascade does not touch disk
    for notebook_id in notebook_ids:
        nb_storage_dir = STORAGE_DIR / "notebooks" / str(notebook_id)
        if nb_storage_dir.is_dir():
            try:
                shutil.rmtree(nb_storage_dir)
            except Exception as e:
                logger.warning(
                    "Could not remove notebook storage %s: %s",
                    nb_storage_dir,
                    e,
                )