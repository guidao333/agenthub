"""Admin routes: review, pricing, user management, finance"""
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import (
    get_db, Capability, User, CallLog, Invoice,
    Subscription, Withdrawal, Review
)
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])

# Require admin for all routes
admin_required = require_role("admin")


# ---- Capability Review ----

@router.get("/reviews/pending")
def pending_reviews(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """List capabilities pending review"""
    caps = db.query(Capability).filter(
        Capability.status == "submitted"
    ).order_by(Capability.updated_at).all()

    result = []
    for cap in caps:
        dev = db.query(User).filter(User.id == cap.developer_id).first()
        result.append({
            "id": cap.id,
            "cap_id": cap.cap_id,
            "name": cap.name,
            "description": cap.description,
            "category": cap.category,
            "developer": dev.username if dev else "unknown",
            "version": cap.version,
            "pricing_model": cap.pricing_model,
            "price": cap.price,
            "submitted_at": cap.updated_at,
        })
    return result


@router.post("/reviews/{cap_id}/approve")
def approve_review(
    cap_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Approve a capability and publish it"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.status != "submitted":
        raise HTTPException(400, f"Status is '{cap.status}', not 'submitted'")

    now = datetime.now(timezone.utc).isoformat()
    cap.status = "published"
    cap.published_at = now
    cap.updated_at = now
    db.commit()
    return {"status": "published", "cap_id": cap.cap_id}


@router.post("/reviews/{cap_id}/reject")
def reject_review(
    cap_id: str,
    reason: str = "",
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Reject a capability"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.status != "submitted":
        raise HTTPException(400, f"Status is '{cap.status}', not 'submitted'")

    cap.status = "rejected"
    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "rejected", "cap_id": cap.cap_id, "reason": reason}


# ---- Pricing Management ----

class PricingUpdate(BaseModel):
    pricing_model: str | None = None
    price: float | None = None


@router.put("/pricing/{cap_id}")
def update_pricing(
    cap_id: str,
    req: PricingUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Set pricing for a capability"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    if req.pricing_model:
        cap.pricing_model = req.pricing_model
    if req.price is not None:
        cap.price = req.price
    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"cap_id": cap.cap_id, "pricing_model": cap.pricing_model, "price": cap.price}


# ---- User Management ----

@router.get("/users")
def list_users(
    role: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """List all users with filters"""
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page-1)*size).limit(size).all()

    return {
        "total": total,
        "items": [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "balance": u.balance,
            "earnings": u.earnings,
            "status": u.status,
            "created_at": u.created_at,
        } for u in users]
    }


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(400, "Cannot suspend admin")
    user.status = "suspended"
    db.commit()
    return {"status": "suspended"}


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.status = "active"
    db.commit()
    return {"status": "active"}


# ---- Finance ----

@router.get("/finance/overview")
def finance_overview(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Platform financial overview"""
    # Total revenue from all calls
    total_revenue = db.query(func.sum(CallLog.charged)).filter(
        CallLog.status == "success"
    ).scalar() or 0

    # This month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
    month_revenue = db.query(func.sum(CallLog.charged)).filter(
        CallLog.status == "success",
        CallLog.created_at >= month_start,
    ).scalar() or 0

    total_calls = db.query(func.count(CallLog.id)).filter(
        CallLog.status == "success"
    ).scalar() or 0

    month_calls = db.query(func.count(CallLog.id)).filter(
        CallLog.status == "success",
        CallLog.created_at >= month_start,
    ).scalar() or 0

    # Pending withdrawals
    pending_withdrawals = db.query(func.sum(Withdrawal.amount)).filter(
        Withdrawal.status == "pending"
    ).scalar() or 0

    user_count = db.query(func.count(User.id)).filter(User.role == "customer").scalar()
    dev_count = db.query(func.count(User.id)).filter(User.role == "developer").scalar()
    cap_count = db.query(func.count(Capability.id)).filter(Capability.status == "published").scalar()

    return {
        "total_revenue": round(float(total_revenue), 2),
        "month_revenue": round(float(month_revenue), 2),
        "platform_cut": round(float(total_revenue) * 0.30, 2),  # 30% platform
        "total_calls": total_calls,
        "month_calls": month_calls,
        "pending_withdrawals": round(float(pending_withdrawals), 2),
        "users": {
            "customers": user_count,
            "developers": dev_count,
            "published_capabilities": cap_count,
        }
    }


@router.get("/finance/withdrawals")
def list_withdrawals(
    status: str | None = None,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """List withdrawal requests"""
    q = db.query(Withdrawal)
    if status:
        q = q.filter(Withdrawal.status == status)
    withdrawals = q.order_by(Withdrawal.applied_at.desc()).limit(50).all()

    return [{
        "id": w.id,
        "developer_id": w.developer_id,
        "amount": w.amount,
        "status": w.status,
        "applied_at": w.applied_at,
        "processed_at": w.processed_at,
    } for w in withdrawals]


@router.post("/finance/withdrawals/{wid}/approve")
def approve_withdrawal(
    wid: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    w = db.query(Withdrawal).filter(Withdrawal.id == wid).first()
    if not w:
        raise HTTPException(404, "Withdrawal not found")
    w.status = "approved"
    w.processed_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "approved"}


@router.post("/finance/withdrawals/{wid}/reject")
def reject_withdrawal(
    wid: int,
    reason: str = "",
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    w = db.query(Withdrawal).filter(Withdrawal.id == wid).first()
    if not w:
        raise HTTPException(404, "Withdrawal not found")
    # Refund to developer
    dev = db.query(User).filter(User.id == w.developer_id).first()
    if dev:
        dev.earnings += w.amount
    w.status = "rejected"
    w.processed_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "rejected", "refunded": w.amount}


# ---- Statistics ----

@router.get("/stats")
def platform_stats(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Quick platform statistics"""
    return {
        "users": db.query(func.count(User.id)).scalar(),
        "capabilities": db.query(func.count(Capability.id)).scalar(),
        "published": db.query(func.count(Capability.id)).filter(Capability.status == "published").scalar(),
        "subscriptions": db.query(func.count(Subscription.id)).filter(Subscription.status == "active").scalar(),
        "total_calls": db.query(func.count(CallLog.id)).scalar(),
        "reviews_pending": db.query(func.count(Capability.id)).filter(Capability.status == "submitted").scalar(),
    }
