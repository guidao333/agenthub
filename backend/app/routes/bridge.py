"""Bridge Protocol v1 - 桥接协议路由

客户侧 OpenClaw 通过此协议与 AgentHub 云端通信。
云端运行 LLM + Agent 逻辑，客户侧桥接 Skill 执行本地设备操作。
"""

import time
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..models import get_db, User, BridgeSession, Capability, CallLog
from ..utils.errors import ErrorCode, AppException, api_response
from ..utils.helpers import now_timestamp, parse_json_field, serialize_json
from .auth import get_current_user

logger = logging.getLogger("agenthub.bridge")
router = APIRouter()


class BridgeStartRequest(BaseModel):
    capability_id: str          # 能力标识
    allowed_tools: list[str] = []  # 允许云端调用的工具白名单


class BridgeMessageRequest(BaseModel):
    session_id: str
    message: str


class BridgeExecResult(BaseModel):
    session_id: str
    tool_id: str
    status: str                  # success / error
    data: dict = {}
    error_msg: str = ""


# ── 建立桥接会话 ──

@router.post("/start")
def bridge_start(req: BridgeStartRequest, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """客户侧桥接 Skill 发起连接，建立会话"""
    cap = db.query(Capability).filter(Capability.cap_id == req.capability_id).first()
    if not cap:
        raise AppException(ErrorCode.CAP_NOT_FOUND)
    if cap.status != "published":
        raise AppException(ErrorCode.CAP_NOT_AVAILABLE)

    session = BridgeSession(
        id=uuid4().hex,
        customer_id=current_user.id,
        capability_id=cap.id,
        status="active",
        allowed_tools=serialize_json(req.allowed_tools or ["ssh_execute", "snmp_get", "http_request", "ping_check"]),
        context="[]",
        last_activity=int(time.time() * 1000),
        created_at=now_timestamp(),
        updated_at=now_timestamp(),
    )
    db.add(session)
    db.commit()

    return api_response(data={
        "session_id": session.id,
        "capability": {
            "id": cap.cap_id,
            "name": cap.name,
            "version": cap.version,
        },
        "allowed_tools": parse_json_field(session.allowed_tools),
        "expires_in_minutes": 30,
    })


# ── 发送消息 → 返回指令 ──

@router.post("/message")
def bridge_message(req: BridgeMessageRequest, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """客户发送用户消息，云端 LLM 处理并返回回复或执行指令"""
    session = db.query(BridgeSession).filter(
        BridgeSession.id == req.session_id,
        BridgeSession.customer_id == current_user.id,
        BridgeSession.status == "active",
    ).first()
    if not session:
        raise AppException(ErrorCode.BRIDGE_SESSION_NOT_FOUND)

    # 检查会话是否超时
    now_ms = int(time.time() * 1000)
    if now_ms - session.last_activity > 30 * 60 * 1000:  # 30 min
        session.status = "expired"
        db.commit()
        raise AppException(ErrorCode.BRIDGE_SESSION_EXPIRED)

    # 更新活动时间
    session.last_activity = now_ms

    # 获取能力信息
    cap = db.query(Capability).filter(Capability.id == session.capability_id).first()
    if not cap:
        raise AppException(ErrorCode.CAP_NOT_FOUND)

    # 记录用户消息到上下文
    context = parse_json_field(session.context, [])
    context.append({"role": "user", "content": req.message})

    # ⚡ 这里以后会集成 LLM Function Calling
    # MVP 阶段：根据消息关键词做简单的意图匹配
    # 完整版：调用 DeepSeek Chat API + 能力包的 SOUL.md + tools 定义
    from ..services.chat_engine import process_message

    try:
        result = process_message(
            message=req.message,
            capability=cap,
            context=context,
            allowed_tools=parse_json_field(session.allowed_tools),
        )
    except Exception as e:
        logger.error(f"Bridge message processing error: {e}")
        raise AppException(ErrorCode.CALL_LLM_ERROR, detail=str(e))

    # 更新上下文
    if result.get("type") == "final_reply":
        context.append({"role": "assistant", "content": result.get("content", "")})
    # tool_call 类型的指令由客户执行，结果回传后云端再处理
    # 所以上下文在这里只保存用户消息，tool_call 和 exec_result 在桥接会话中流转

    session.context = serialize_json(context)
    db.commit()

    # 记录调用日志（最终回复时才记录）
    if result.get("type") == "final_reply":
        log = CallLog(
            capability_id=session.capability_id,
            customer_id=current_user.id,
            session_id=session.id,
            mode="bridge",
            status="success",
            charged=0,  # 暂不计费，后续计费系统完善后启
            created_at=now_timestamp(),
        )
        db.add(log)
        db.commit()

    return api_response(data=result)


# ── 回传执行结果 ──

@router.post("/exec-result")
def bridge_exec_result(req: BridgeExecResult, current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """客户侧桥接 Skill 回传本地执行结果"""
    session = db.query(BridgeSession).filter(
        BridgeSession.id == req.session_id,
        BridgeSession.customer_id == current_user.id,
        BridgeSession.status == "active",
    ).first()
    if not session:
        raise AppException(ErrorCode.BRIDGE_SESSION_NOT_FOUND)

    session.last_activity = int(time.time() * 1000)

    # 更新上下文：记录工具执行结果
    context = parse_json_field(session.context, [])
    context.append({
        "role": "tool",
        "tool_call_id": req.tool_id,
        "status": req.status,
        "content": req.error_msg if req.status == "error" else serialize_json(req.data),
    })

    session.context = serialize_json(context)
    db.commit()

    return api_response(data={
        "received": True,
        "tool_id": req.tool_id,
        "status": req.status,
    })


# ── 关闭桥接会话 ──

@router.post("/close")
def bridge_close(session_id: str, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """关闭桥接会话"""
    session = db.query(BridgeSession).filter(
        BridgeSession.id == session_id,
        BridgeSession.customer_id == current_user.id,
    ).first()
    if not session:
        raise AppException(ErrorCode.BRIDGE_SESSION_NOT_FOUND)

    session.status = "closed"
    session.updated_at = now_timestamp()
    db.commit()

    return api_response(data={"session_id": session_id, "status": "closed"})


# ── 会话状态查询 ──

@router.get("/status/{session_id}")
def bridge_status(session_id: str, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """查询桥接会话状态"""
    session = db.query(BridgeSession).filter(
        BridgeSession.id == session_id,
        BridgeSession.customer_id == current_user.id,
    ).first()
    if not session:
        raise AppException(ErrorCode.BRIDGE_SESSION_NOT_FOUND)

    return api_response(data={
        "session_id": session.id,
        "status": session.status,
        "capability_id": session.capability_id,
        "allowed_tools": parse_json_field(session.allowed_tools),
        "message_count": len(parse_json_field(session.context, [])),
        "last_activity": session.last_activity,
        "created_at": session.created_at,
    })
