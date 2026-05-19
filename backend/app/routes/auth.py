"""Authentication and authorization v2.0"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from jose import JWTError, jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    NEW_USER_BONUS,
)
from ..models import get_db, User
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ── Models ──

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
    refresh_token: str
    token_type: str = "bearer"


# ── Helpers ──

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── Dependencies ──

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT Token 或 API Key 获取当前用户"""
    # 优先 API Key 认证
    if api_key:
        from ..models import Subscription
        sub = db.query(Subscription).filter(Subscription.api_key == api_key).first()
        if sub:
            user = db.query(User).filter(User.id == sub.customer_id).first()
            if user:
                return user
        raise AppException(ErrorCode.AUTH_API_KEY_INVALID)

    # JWT 认证
    if not token:
        raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
    except JWTError:
        raise AppException(ErrorCode.AUTH_TOKEN_EXPIRED)

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
    if user.status != "active":
        raise AppException(ErrorCode.AUTH_USER_DISABLED)
    return user


def require_role(*roles: str):
    """Dependency: require specific role(s)"""
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise AppException(ErrorCode.AUTH_PERMISSION_DENIED)
        return current_user
    return checker


# ── Routes ──

@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户"""
    if db.query(User).filter(User.username == req.username).first():
        raise AppException(ErrorCode.AUTH_USERNAME_TAKEN)
    if db.query(User).filter(User.email == req.email).first():
        raise AppException(ErrorCode.AUTH_EMAIL_TAKEN)

    if req.role not in ("customer", "developer"):
        req.role = "customer"

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        balance=NEW_USER_BONUS,  # 赠送余额
        created_at=now_timestamp(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return api_response(data={
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "balance": user.balance,
    })


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """登录"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
    if user.status != "active":
        raise AppException(ErrorCode.AUTH_USER_DISABLED)

    access_token = create_access_token({"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username})

    return api_response(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "balance": user.balance,
        },
    })


@router.post("/auth/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    """刷新 Token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise AppException(ErrorCode.AUTH_INVALID_CREDENTIALS)
    except JWTError:
        raise AppException(ErrorCode.AUTH_TOKEN_EXPIRED)

    new_access = create_access_token({"sub": user.username, "role": user.role})
    return api_response(data={
        "access_token": new_access,
        "token_type": "bearer",
    })


@router.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return api_response(data={
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "balance": current_user.balance,
        "status": current_user.status,
        "created_at": current_user.created_at,
    })
