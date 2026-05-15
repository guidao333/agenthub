"""API call routes: direct capability invocation"""
import json
import uuid
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..models import get_db, Subscription, Capability, CallLog
from ..config import RATE_LIMIT_PER_MINUTE

router = APIRouter(prefix="/api", tags=["api-call"])

# Simple in-memory rate limiter
_rate_store: dict[str, list[float]] = {}


class APICallRequest(BaseModel):
    input: str
    params: dict = {}


class APICallResponse(BaseModel):
    call_id: str
    output: str
    duration_ms: int
    charged: float
    status: str


def check_rate_limit(api_key: str) -> bool:
    """Simple rate limit: max N requests per minute per key"""
    now = time.time()
    if api_key not in _rate_store:
        _rate_store[api_key] = []

    # Clean old entries
    _rate_store[api_key] = [t for t in _rate_store[api_key] if now - t < 60]

    if len(_rate_store[api_key]) >= RATE_LIMIT_PER_MINUTE:
        return False

    _rate_store[api_key].append(now)
    return True


@router.post("/call/{cap_id}")
def call_capability(
    cap_id: str,
    req: APICallRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Direct API call to a capability"""
    # Verify API key
    sub = db.query(Subscription).filter(
        Subscription.api_key == x_api_key,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise HTTPException(401, "Invalid API key")

    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap or cap.status != "published":
        raise HTTPException(404, "Capability not found")

    if sub.capability_id != cap.id:
        raise HTTPException(403, "API key not valid for this capability")

    # Rate limit
    if not check_rate_limit(x_api_key):
        raise HTTPException(429, "Rate limit exceeded")

    # Execute
    call_id = str(uuid.uuid4())
    start_time = time.time()
    status = "success"
    output = ""

    try:
        from ..services.chat_engine import ChatEngine
        engine = ChatEngine(capability=cap)
        # For API mode, create a simple single-turn conversation
        history = [{"role": "user", "content": req.input}]

        import asyncio
        result_parts = []
        async def collect():
            async for chunk in engine.stream_chat(history):
                if isinstance(chunk, dict):
                    continue
                result_parts.append(chunk)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    loop.run_in_executor(pool, lambda: asyncio.run(collect()))
            else:
                loop.run_until_complete(collect())
        except RuntimeError:
            asyncio.run(collect())

        output = "".join(result_parts)
    except Exception as e:
        status = "error"
        output = str(e)

    duration_ms = int((time.time() - start_time) * 1000)
    charged = cap.price if status == "success" and cap.pricing_model == "per_call" else 0

    # Log
    log = CallLog(
        subscription_id=sub.id,
        capability_id=cap.id,
        session_id=call_id,
        input_summary=req.input[:200],
        output_summary=output[:200],
        duration_ms=duration_ms,
        status=status,
        charged=charged,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(log)
    if status == "success":
        cap.call_count += 1
    db.commit()

    return APICallResponse(
        call_id=call_id,
        output=output,
        duration_ms=duration_ms,
        charged=charged,
        status=status,
    )
