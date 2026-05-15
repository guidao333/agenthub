"""Chat routes: create sessions, send messages (SSE streaming)"""
import json
import uuid
import time
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..models import get_db, ChatSession, Subscription, Capability, CallLog, User
from ..auth import get_current_user
from ..services.chat_engine import ChatEngine
from ..config import MAX_CONTEXT_TURNS

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    capability_id: str  # cap_id string


class SendMessageRequest(BaseModel):
    message: str


@router.post("/sessions")
def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session for a capability"""
    cap = db.query(Capability).filter(Capability.cap_id == req.capability_id).first()
    if not cap or cap.status != "published":
        raise HTTPException(404, "Capability not found")

    # Verify subscription
    sub = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise HTTPException(403, "Not subscribed to this capability")

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    chat_session = ChatSession(
        id=session_id,
        user_id=current_user.id,
        capability_id=cap.id,
        context=json.dumps([]),
        created_at=now,
        updated_at=now,
    )
    db.add(chat_session)
    db.commit()

    return {"session_id": session_id, "capability": cap.name}


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message and get streaming response"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
        ChatSession.status == "active",
    ).first()
    if not chat_session:
        raise HTTPException(404, "Session not found")

    cap = db.query(Capability).filter(Capability.id == chat_session.capability_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    # Load conversation history
    history = json.loads(chat_session.context) if chat_session.context else []
    history.append({"role": "user", "content": req.message})

    # Get subscription for billing
    sub = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()

    start_time = time.time()
    engine = ChatEngine(capability=cap)

    async def generate():
        full_response = ""
        tool_calls_count = 0
        token_in = 0
        token_out = 0
        status = "success"

        try:
            async for chunk in engine.stream_chat(history):
                if isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                    tool_calls_count += 1
                    continue
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Update history
            history.append({"role": "assistant", "content": full_response})
            # Trim to max turns
            if len(history) > MAX_CONTEXT_TURNS * 2:
                history = history[-(MAX_CONTEXT_TURNS * 2):]
            chat_session.context = json.dumps(history)
            chat_session.updated_at = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            status = "error"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            full_response = str(e)
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            # Log call
            log = CallLog(
                subscription_id=sub.id if sub else None,
                capability_id=cap.id,
                session_id=session_id,
                input_summary=req.message[:200],
                output_summary=full_response[:200],
                tool_calls=tool_calls_count,
                duration_ms=duration_ms,
                token_input=token_in,
                token_output=token_out,
                status=status,
                charged=cap.price if status == "success" and cap.pricing_model == "per_call" else 0,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            db.add(log)
            if status == "success":
                cap.call_count += 1
            db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/sessions/{session_id}/history")
def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chat session history"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not chat_session:
        raise HTTPException(404, "Session not found")

    history = json.loads(chat_session.context) if chat_session.context else []
    return {"session_id": session_id, "history": history}


@router.delete("/sessions/{session_id}")
def close_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Close a chat session"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not chat_session:
        raise HTTPException(404, "Session not found")

    chat_session.status = "closed"
    db.commit()
    return {"status": "closed"}
