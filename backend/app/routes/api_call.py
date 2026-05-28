"""API call routes: direct capability invocation (v2.0)"""

import json
import time
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..models import get_db, Subscription, Capability, CallLog, User
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp, new_trace_id
from ..middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/api", tags=["api-call"])


class APICallRequest(BaseModel):
    input: str
    params: dict = {}


@router.post("/call/{cap_id}")
def call_capability(
    cap_id: str,
    req: APICallRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Call a capability with a customer-bound API key."""
    identity_sub = db.query(Subscription).filter(
        Subscription.api_key == x_api_key,
        Subscription.status == "active",
    ).first()
    if not identity_sub:
        raise AppException(ErrorCode.AUTH_API_KEY_INVALID)

    if not rate_limiter.check(f"apikey_{x_api_key[:12]}"):
        raise AppException(ErrorCode.CALL_RATE_LIMIT)

    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap or cap.status != "published":
        raise AppException(ErrorCode.CAP_NOT_FOUND)

    target_sub = db.query(Subscription).filter(
        Subscription.customer_id == identity_sub.customer_id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if not target_sub:
        raise AppException(ErrorCode.AUTH_PERMISSION_DENIED, detail="客户未订阅该能力或订阅已失效")

    # 执行
    call_id = f"call_{new_trace_id()}"
    trace_id = new_trace_id()
    start_time = time.time()
    status = "success"
    output = ""

    try:
        from ..services.chat_engine import process_message
        result = process_message(
            message=req.input,
            capability=cap,
            context=[{"role": "user", "content": req.input}],
        )
        output = result.get("content", "处理完成")
    except Exception as e:
        status = "error"
        output = f"错误: {str(e)}"

    duration_ms = int((time.time() - start_time) * 1000)
    charged = cap.price if (status == "success" and cap.pricing_model == "per_call" and cap.price > 0) else 0

    # 记录日志
    log = CallLog(
        subscription_id=target_sub.id,
        capability_id=cap.id,
        customer_id=identity_sub.customer_id,
        session_id=call_id,
        trace_id=trace_id,
        mode="cloud",
        input_summary=req.input[:200],
        output_summary=output[:200],
        duration_ms=duration_ms,
        status=status,
        charged=charged,
        created_at=now_timestamp(),
    )
    db.add(log)
    if status == "success":
        cap.call_count += 1
    db.commit()

    return api_response(data={
        "call_id": call_id,
        "output": output,
        "duration_ms": duration_ms,
        "charged": charged,
        "status": status,
    })


@router.get("/call/{call_id}/result")
def get_call_result(
    call_id: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """查询调用结果"""
    log = db.query(CallLog).filter(CallLog.session_id == call_id).first()
    if not log:
        raise AppException(ErrorCode.COMMON_NOT_FOUND)

    return api_response(data={
        "call_id": call_id,
        "status": log.status,
        "output": log.output_summary,
        "duration_ms": log.duration_ms,
        "charged": log.charged,
        "created_at": log.created_at,
    })
