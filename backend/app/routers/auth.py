import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Schemas ───────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
    password: str


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
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Routes ────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Passwords are bcrypt-hashed."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=pwd_ctx.hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Placeholder login — returns a stub token. Wire JWT later."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # TODO: verify password + issue real JWT
    return {"access_token": f"stub-token-for-{user.id}", "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(db: Session = Depends(get_db)):
    """Placeholder — returns the demo user. Replace with JWT auth dep."""
    user = db.query(User).filter(User.email == "demo@gemini.local").first()
    if not user:
        raise HTTPException(status_code=404, detail="Demo user not found")
    return user
