"""Customer dashboard routes: subscriptions, usage, billing, API keys"""
from datetime import datetime, timezone
import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import get_db, Subscription, Capability, CallLog, User, Invoice
from ..auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---- Subscriptions ----

@router.get("/subscriptions")
def my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active subscriptions"""
    subs = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
    ).order_by(Subscription.started_at.desc()).all()

    result = []
    for sub in subs:
        cap = db.query(Capability).filter(Capability.id == sub.capability_id).first()
        result.append({
            "id": sub.id,
            "capability_id": sub.capability_id,
            "cap_id": cap.cap_id if cap else "",
            "capability_name": cap.name if cap else "Unknown",
            "status": sub.status,
            "api_key": sub.api_key,
            "started_at": sub.started_at,
            "expires_at": sub.expires_at,
        })
    return result


# ---- Usage Stats ----

@router.get("/usage")
def usage_stats(
    period: str = "month",  # week / month / total
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage statistics"""
    sub_ids = [s.id for s in db.query(Subscription).filter(
        Subscription.customer_id == current_user.id
    ).all()]

    if not sub_ids:
        return {"total_calls": 0, "total_charged": 0, "by_capability": []}

    now = datetime.now(timezone.utc)
    if period == "week":
        start = (now - __import__("datetime").timedelta(days=7)).isoformat()
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
    else:
        start = "2000-01-01"

    logs = db.query(CallLog).filter(
        CallLog.subscription_id.in_(sub_ids),
        CallLog.created_at >= start,
    ).all()

    total_calls = len(logs)
    total_charged = sum(l.charged for l in logs)

    # Group by capability
    cap_calls = {}
    for log in logs:
        cap_calls.setdefault(log.capability_id, {"calls": 0, "charged": 0})
        cap_calls[log.capability_id]["calls"] += 1
        cap_calls[log.capability_id]["charged"] += log.charged

    by_cap = []
    for cap_id, data in cap_calls.items():
        cap = db.query(Capability).filter(Capability.id == cap_id).first()
        by_cap.append({
            "cap_id": cap.cap_id if cap else "",
            "name": cap.name if cap else "Unknown",
            "calls": data["calls"],
            "charged": round(data["charged"], 2),
        })

    return {
        "total_calls": total_calls,
        "total_charged": round(total_charged, 2),
        "by_capability": sorted(by_cap, key=lambda x: x["calls"], reverse=True),
    }


# ---- Bills ----

@router.get("/bills")
def list_bills(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List invoices"""
    q = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    total = q.count()
    bills = q.order_by(Invoice.created_at.desc()).offset((page-1)*size).limit(size).all()

    return {
        "total": total,
        "items": [{
            "id": b.id,
            "type": b.type,
            "amount": b.amount,
            "status": b.status,
            "period_start": b.period_start,
            "period_end": b.period_end,
            "created_at": b.created_at,
        } for b in bills]
    }


# ---- Recharge ----

class RechargeRequest(BaseModel):
    amount: float
    payment_method: str = "manual"  # MVP: manual recharge by admin


@router.post("/recharge")
def request_recharge(
    req: RechargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request balance recharge (MVP: manual process)"""
    if req.amount <= 0:
        raise HTTPException(400, "Amount must be positive")

    # MVP: just add balance directly (admin manually processes payments)
    # In production: integrate payment gateway
    invoice = Invoice(
        user_id=current_user.id,
        type="charge",
        amount=req.amount,
        status="pending",
        detail=json.dumps({"method": req.payment_method, "note": "MVP manual recharge"}),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(invoice)
    db.commit()
    return {"invoice_id": invoice.id, "amount": req.amount, "status": "pending"}


# ---- API Keys ----

@router.get("/api-keys")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List API keys for active subscriptions"""
    subs = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.status == "active",
    ).all()

    return [{
        "subscription_id": s.id,
        "api_key": s.api_key,
        "capability_name": db.query(Capability).filter(Capability.id == s.capability_id).first().name if db.query(Capability).filter(Capability.id == s.capability_id).first() else "Unknown",
    } for s in subs]


@router.post("/api-keys")
def regenerate_api_key(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate API key for a subscription"""
    sub = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.customer_id == current_user.id,
    ).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    sub.api_key = f"ahk_{secrets.token_hex(24)}"
    db.commit()
    return {"api_key": sub.api_key}
