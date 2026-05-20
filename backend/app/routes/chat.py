"""Chat routes: create sessions, send messages (SSE streaming)"""

import json
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..models import get_db, ChatSession, Subscription, Capability, CallLog, User
from ..auth import get_current_user
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp, new_session_id, new_trace_id
from ..config import MAX_CONTEXT_TURNS, MAX_TOOL_CALL_ROUNDS

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    capability_id: str


class SendMessageRequest(BaseModel):
    message: str



@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's chat sessions"""
    from ..models import ChatSession, Capability
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.status == "active",
    ).order_by(ChatSession.updated_at.desc()).limit(50).all()

    result = []
    for s in sessions:
        cap = db.query(Capability).filter(Capability.id == s.capability_id).first()
        result.append({
            "id": s.id,
            "capability_id": s.capability_id,
            "capability_name": cap.name if cap else "unknown",
            "status": s.status,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return result


@router.post("/sessions")
def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建对话会话"""
    cap = db.query(Capability).filter(Capability.cap_id == req.capability_id).first()
    if not cap or cap.status != "published":
        raise AppException(ErrorCode.CAP_NOT_FOUND)

    # 检查订阅
    sub = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise AppException(ErrorCode.CAP_NOT_SUBSCRIBED)

    session_id = uuid.uuid4().hex
    now = now_timestamp()
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

    return api_response(data={
        "session_id": session_id,
        "capability": cap.name,
        "cap_id": cap.cap_id,
    })


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发送消息并获取流式响应"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
        ChatSession.status == "active",
    ).first()
    if not chat_session:
        raise AppException(ErrorCode.COMMON_NOT_FOUND, detail="会话不存在或已关闭")

    cap = db.query(Capability).filter(Capability.id == chat_session.capability_id).first()
    if not cap:
        raise AppException(ErrorCode.CAP_NOT_FOUND)

    # 检查订阅
    sub = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()

    # 加载对话历史
    history = json.loads(chat_session.context) if chat_session.context else []
    history.append({"role": "user", "content": req.message})

    start_time = time.time()
    trace_id = new_trace_id()

    async def generate():
        full_response = ""
        tool_calls_count = 0
        status = "success"

        try:
            # MVP 简化版：使用同步处理并模拟流式输出
            from ..services.chat_engine import process_message
            result = process_message(
                message=req.message,
                capability=cap,
                context=history,
            )

            if result.get("type") == "tool_call":
                tool_calls_count += 1
                content = f"正在执行 {result.get('tool_name')}..."
            else:
                content = result.get("content", "处理完成")

            full_response = content

            # 模拟流式输出
            import asyncio
            for chunk in [content[i:i+20] for i in range(0, len(content), 20)]:
                yield f"data: {json.dumps({'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # 更新对话历史
            history.append({"role": "assistant", "content": full_response})
            if len(history) > MAX_CONTEXT_TURNS * 2:
                history = history[-(MAX_CONTEXT_TURNS * 2):]
            chat_session.context = json.dumps(history)
            chat_session.updated_at = now_timestamp()

        except Exception as e:
            status = "error"
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            full_response = str(e)

        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            charged = cap.price if (status == "success" and cap.pricing_model == "per_call" and cap.price > 0) else 0

            log = CallLog(
                subscription_id=sub.id if sub else None,
                capability_id=cap.id,
                customer_id=current_user.id,
                session_id=session_id,
                trace_id=trace_id,
                mode="cloud",
                input_summary=req.message[:200],
                output_summary=full_response[:200],
                tool_calls=tool_calls_count,
                duration_ms=duration_ms,
                status=status,
                charged=charged,
                created_at=now_timestamp(),
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
    """获取对话历史"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not chat_session:
        raise AppException(ErrorCode.COMMON_NOT_FOUND)

    history = json.loads(chat_session.context) if chat_session.context else []
    return api_response(data={"session_id": session_id, "history": history})


@router.delete("/sessions/{session_id}")
def close_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """关闭会话"""
    chat_session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not chat_session:
        raise AppException(ErrorCode.COMMON_NOT_FOUND)

    chat_session.status = "closed"
    chat_session.updated_at = now_timestamp()
    db.commit()
    return api_response(data={"session_id": session_id, "status": "closed"})
