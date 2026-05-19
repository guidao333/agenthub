"""计费系统路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db, User, Invoice, Withdrawal, CallLog
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp, parse_json_field
from .auth import get_current_user, require_role

router = APIRouter()


class RechargeRequest(BaseModel):
    amount: float
    remark: str = ""


# ── 余额查询 ──

@router.get("/billing/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    """查询余额"""
    return api_response(data={
        "balance": current_user.balance,
        "frozen_balance": current_user.frozen_balance,
        "available_balance": max(0, current_user.balance - current_user.frozen_balance),
        "earnings": current_user.earnings if current_user.role == "developer" else 0,
    })


# ── 充值 ──

@router.post("/billing/recharge")
def recharge(req: RechargeRequest, current_user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """充值（客户/开发者通用）"""
    if req.amount <= 0:
        raise AppException(ErrorCode.BILL_INVALID_AMOUNT)

    current_user.balance += req.amount

    invoice = Invoice(
        user_id=current_user.id,
        type="charge",
        amount=req.amount,
        status="settled",
        period_start=now_timestamp(),
        period_end=now_timestamp(),
        detail=f'{{"remark": "{req.remark}"}}',
        created_at=now_timestamp(),
    )
    db.add(invoice)
    db.commit()

    return api_response(data={
        "balance": current_user.balance,
        "amount": req.amount,
        "invoice_id": invoice.id,
    })


# ── 账单明细 ──

@router.get("/billing/invoices")
def list_invoices(page: int = 1, size: int = 20,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """账单明细"""
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    total = query.count()
    invoices = query.order_by(Invoice.id.desc()).offset((page - 1) * size).limit(size).all()

    return api_response(data={
        "items": [{
            "id": inv.id,
            "type": inv.type,
            "amount": inv.amount,
            "status": inv.status,
            "period": f"{inv.period_start} ~ {inv.period_end}",
            "detail": parse_json_field(inv.detail),
            "created_at": inv.created_at,
        } for inv in invoices],
        "total": total,
        "page": page,
        "size": size,
    })


# ── 调用费用明细 ──

@router.get("/billing/call-logs")
def list_call_logs(page: int = 1, size: int = 20,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """调用费用明细"""
    query = db.query(CallLog).filter(CallLog.customer_id == current_user.id)
    total = query.count()
    logs = query.order_by(CallLog.id.desc()).offset((page - 1) * size).limit(size).all()

    from ..models import Capability
    cap_map = {c.id: c for c in db.query(Capability).all()}

    return api_response(data={
        "items": [{
            "id": log.id,
            "capability_name": cap_map.get(log.capability_id, {}).name if hasattr(cap_map.get(log.capability_id), "name") else f"#{log.capability_id}",
            "status": log.status,
            "charged": log.charged,
            "duration_ms": log.duration_ms,
            "trace_id": log.trace_id,
            "mode": log.mode,
            "created_at": log.created_at,
        } for log in logs],
        "total": total,
        "page": page,
        "size": size,
    })


# ── 开发者提现 ──

@router.post("/billing/withdraw")
def withdraw(amount: float, current_user: User = Depends(require_role("developer")),
             db: Session = Depends(get_db)):
    """申请提现"""
    if amount < 100:
        raise AppException(ErrorCode.BILL_MIN_WITHDRAW)
    if current_user.earnings < amount:
        raise AppException(ErrorCode.BILL_INSUFFICIENT_BALANCE, detail=f"可提现余额: {current_user.earnings}")

    # 冻结提现金额
    current_user.earnings -= amount

    withdrawal = Withdrawal(
        developer_id=current_user.id,
        amount=amount,
        status="pending",
        applied_at=now_timestamp(),
    )
    db.add(withdrawal)
    db.commit()

    return api_response(data={
        "withdrawal_id": withdrawal.id,
        "amount": amount,
        "status": "pending",
        "note": "提现申请已提交，管理员审核后 3 个工作日内到账",
    })


# ── 提现记录 ──

@router.get("/billing/withdrawals")
def list_withdrawals(current_user: User = Depends(require_role("developer")),
                     db: Session = Depends(get_db)):
    """提现记录"""
    records = (db.query(Withdrawal)
               .filter(Withdrawal.developer_id == current_user.id)
               .order_by(Withdrawal.id.desc())
               .limit(50).all())

    return api_response(data=[{
        "id": w.id,
        "amount": w.amount,
        "status": w.status,
        "applied_at": w.applied_at,
        "processed_at": w.processed_at or "待处理",
    } for w in records])
