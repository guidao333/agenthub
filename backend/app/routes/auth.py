"""Auth routes: register, login, refresh"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from ..models import get_db, User, init_db
from ..auth import hash_password, verify_password, create_access_token
from ..config import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "customer"  # customer / developer


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.role not in ("customer", "developer"):
        raise HTTPException(400, "Role must be 'customer' or 'developer'")

    # Check duplicates
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "Username already exists")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already exists")

    now = datetime.now(timezone.utc).isoformat()
    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        created_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    if user.status != "active":
        raise HTTPException(403, "Account is suspended")

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@router.post("/refresh", response_model=TokenResponse)
def refresh(current_user: User = Depends(lambda: None)):
    # Simplified: just re-issue
    from ..auth import get_current_user, oauth2_scheme
    from fastapi import Request
    raise HTTPException(501, "Use login instead")
