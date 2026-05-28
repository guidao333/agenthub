"""Customer dashboard routes: subscriptions, usage, billing, API keys"""

import json
import time
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import get_db, Subscription, Capability, CallLog, User, Invoice
from ..auth import get_current_user
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp, new_api_key

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/client-status")
def client_status(current_user: User = Depends(get_current_user)):
    """Return online AgentHub desktop clients for the current customer."""
    try:
        from ..routes.ws_client import manager as ws_manager

        devices = ws_manager.get_devices_for_customer(current_user.id)
        return api_response(data={
            "online": bool(devices),
            "online_count": len(devices),
            "server_time": time.time(),
            "devices": devices,
        })
    except Exception as exc:
        return api_response(data={
            "online": False,
            "online_count": 0,
            "server_time": time.time(),
            "devices": [],
            "error": str(exc),
        })


# ---- 已订阅能力 ----

@router.get("/subscriptions")
def my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """已订阅能力列表"""
    subs = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
    ).order_by(Subscription.started_at.desc()).all()

    cap_ids = [s.capability_id for s in subs]
    caps = {c.id: c for c in db.query(Capability).filter(Capability.id.in_(cap_ids)).all()} if cap_ids else {}

    result = [{
        "id": sub.id,
        "capability_id": sub.capability_id,
        "cap_id": caps.get(sub.capability_id).cap_id if sub.capability_id in caps else "",
        "capability_name": caps.get(sub.capability_id).name if sub.capability_id in caps else "Unknown",
        "status": sub.status,
        "api_key": sub.api_key,
        "locked_version": sub.locked_version,
        "started_at": sub.started_at,
        "expires_at": sub.expires_at,
    } for sub in subs]

    return api_response(data=result)


# ---- 用量统计 ----

@router.get("/usage")
def usage_stats(
    period: str = "month",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用量统计"""
    if period == "week":
        from datetime import timedelta, datetime
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        from datetime import datetime
        start = datetime.now().strftime("%Y-%m-01")
    else:
        start = "2000-01-01"

    logs = db.query(CallLog).filter(
        CallLog.customer_id == current_user.id,
        CallLog.created_at >= start,
    ).all()

    total_calls = len(logs)
    total_charged = sum(l.charged for l in logs)

    # 按能力分组
    cap_calls = {}
    for log in logs:
        cap_calls.setdefault(log.capability_id, {"calls": 0, "charged": 0})
        cap_calls[log.capability_id]["calls"] += 1
        cap_calls[log.capability_id]["charged"] += log.charged

    cap_ids = list(cap_calls.keys())
    caps = {c.id: c for c in db.query(Capability).filter(Capability.id.in_(cap_ids)).all()} if cap_ids else {}

    by_cap = [{
        "cap_id": caps.get(cid).cap_id if cid in caps else "",
        "name": caps.get(cid).name if cid in caps else "Unknown",
        "calls": data["calls"],
        "charged": round(data["charged"], 2),
    } for cid, data in sorted(cap_calls.items(), key=lambda x: x[1]["calls"], reverse=True)]

    return api_response(data={
        "total_calls": total_calls,
        "total_charged": round(total_charged, 2),
        "by_capability": by_cap,
    })


# ---- API Key 管理 ----

@router.get("/api-keys")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API Key 列表"""
    subs = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.status == "active",
    ).all()

    cap_ids = [s.capability_id for s in subs]
    caps = {c.id: c.name for c in db.query(Capability).filter(Capability.id.in_(cap_ids)).all()} if cap_ids else {}

    result = [{
        "subscription_id": s.id,
        "api_key": s.api_key,
        "capability_name": caps.get(s.capability_id, "Unknown"),
    } for s in subs]

    return api_response(data=result)


@router.post("/api-keys")
def regenerate_api_key(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重新生成 API Key"""
    sub = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.customer_id == current_user.id,
    ).first()
    if not sub:
        raise AppException(ErrorCode.COMMON_NOT_FOUND, detail="订阅不存在")

    sub.api_key = new_api_key()
    db.commit()
    return api_response(data={"api_key": sub.api_key})


# ---- 客户配置管理 ----

@router.get("/configs")
def list_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出客户配置"""
    from ..models import CustomerConfig
    configs = db.query(CustomerConfig).filter(
        CustomerConfig.customer_id == current_user.id,
    ).all()
    return api_response(data=[{
        "key": c.config_key,
        "value": c.config_value,  # MVP: 明文展示，后续加解密
        "encrypted": bool(c.encrypted),
        "updated_at": c.updated_at,
    } for c in configs])


@router.post("/configs")
def update_config(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新客户配置"""
    from ..models import CustomerConfig
    config = db.query(CustomerConfig).filter(
        CustomerConfig.customer_id == current_user.id,
        CustomerConfig.config_key == key,
    ).first()

    if config:
        config.config_value = value
        config.updated_at = now_timestamp()
    else:
        config = CustomerConfig(
            customer_id=current_user.id,
            config_key=key,
            config_value=value,
            created_at=now_timestamp(),
            updated_at=now_timestamp(),
        )
        db.add(config)

    db.commit()
    return api_response(data={"key": key, "updated": True})


@router.delete("/configs/{key}")
def delete_config(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除客户配置"""
    from ..models import CustomerConfig
    config = db.query(CustomerConfig).filter(
        CustomerConfig.customer_id == current_user.id,
        CustomerConfig.config_key == key,
    ).first()
    if not config:
        raise AppException(ErrorCode.COMMON_NOT_FOUND)
    db.delete(config)
    db.commit()
    return api_response(data={"key": key, "deleted": True})
