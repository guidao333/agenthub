"""Unified capability chat engine.

The platform owns intent understanding and tool selection. Local clients only
receive predefined JSON actions and return execution results.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from ..models import Capability, SessionLocal, Subscription, User
from ..routes.auth import get_current_user
from ..routes.ws_client import manager as ws_manager
from .cap_config import get_customer_config_value

logger = logging.getLogger("agenthub.chat_engine")

router = APIRouter(prefix="/capability-chat", tags=["capability-chat"])

_llm_client = None


def _get_llm():
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _llm_client


CAPABILITY_TOOLS = {
    "isp-smart-cs": {
        "system_prompt": (
            "你是 ISP 宽带运营商的智能客服助手。你只能处理宽带业务相关请求，"
            "包括账号查询、续费、停机、复机、派发工单、查询 ONU 状态、重启 ONU。"
            "当用户表达明确业务意图时，调用对应工具；当缺少账号、月数、联系方式等必要参数时，先追问。"
            "停机、复机、重启 ONU 等有影响的操作，回复时要清楚说明执行结果。"
        ),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "query_account",
                    "description": "查询宽带账号状态、余额、套餐或使用情况",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "宽带账号、手机号或客户编号"},
                            "query_type": {
                                "type": "string",
                                "enum": ["status", "balance", "package", "usage"],
                                "description": "查询类型",
                            },
                        },
                        "required": ["account"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "renew_account",
                    "description": "为宽带账号续费",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "宽带账号"},
                            "months": {"type": "integer", "description": "续费月数", "default": 1},
                            "package_id": {"type": "string", "description": "套餐 ID，可选"},
                        },
                        "required": ["account", "months"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "suspend_account",
                    "description": "暂停或停用宽带账号",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "宽带账号"},
                            "reason": {"type": "string", "description": "停机原因"},
                        },
                        "required": ["account"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reactive_account",
                    "description": "复机或恢复宽带账号",
                    "parameters": {
                        "type": "object",
                        "properties": {"account": {"type": "string", "description": "宽带账号"}},
                        "required": ["account"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_ticket",
                    "description": "派发维修工单",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "宽带账号"},
                            "issue_type": {
                                "type": "string",
                                "enum": ["no_internet", "slow_speed", "onu_fault", "cable_fault", "other"],
                                "description": "故障类型",
                            },
                            "description": {"type": "string", "description": "故障描述"},
                            "contact_phone": {"type": "string", "description": "联系电话"},
                        },
                        "required": ["account", "issue_type", "description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_onu_status",
                    "description": "查询 ONU 光猫在线状态、光功率、版本等信息",
                    "parameters": {
                        "type": "object",
                        "properties": {"account": {"type": "string", "description": "宽带账号或 ONU SN"}},
                        "required": ["account"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reboot_onu",
                    "description": "远程重启 ONU 光猫",
                    "parameters": {
                        "type": "object",
                        "properties": {"account": {"type": "string", "description": "宽带账号或 ONU SN"}},
                        "required": ["account"],
                    },
                },
            },
        ],
    },
    "ai-smart-monitor": {
        "system_prompt": (
            "你是 AI 智能监控助手。你只能处理监控、安防、卫生巡检、事件查询、摄像头状态相关请求。"
            "平台统一接入 RTSP/ONVIF 摄像头，客户现场通常通过 NVR 录像主机保存历史视频，视频分析在客户边缘端运行。"
            "当前已开放工具只支持巡检、事件查询、评分和摄像头状态。"
            "当用户要求录像回查、AI 找人、物品遗失或车辆检索时，先收集摄像头位置、时间范围、目标描述等必要信息，"
            "并说明该类能力需要对应 NVR 品牌适配和边缘端录像分析版本上线后才能执行真实回放检索。"
        ),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "trigger_patrol",
                    "description": "触发一次 AI 巡检",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "camera_location": {"type": "string", "description": "摄像头位置，留空表示全部"},
                            "patrol_type": {
                                "type": "string",
                                "enum": ["hygiene", "safety", "fire_lane", "all"],
                                "description": "巡检类型",
                                "default": "all",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_events",
                    "description": "查询检测事件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "enum": ["trash_detected", "throw_detected", "intrusion", "fire_smoke", "all"],
                                "description": "事件类型",
                            },
                            "hours": {"type": "integer", "description": "查询最近几小时", "default": 24},
                            "location": {"type": "string", "description": "摄像头位置筛选"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_patrol_scores",
                    "description": "获取巡检评分报告",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "位置，留空查全部"},
                            "days": {"type": "integer", "description": "查询最近几天", "default": 7},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_camera_status",
                    "description": "查询摄像头在线状态",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ],
    },
}


class ChatMessage(BaseModel):
    session_id: str
    message: str


class CreateSessionRequest(BaseModel):
    cap_id: str


_sessions: Dict[str, dict] = {}
MAX_SESSIONS = 500
MAX_HISTORY = 40


def _check_subscription(db, user_id: int, cap_id: str):
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "能力不存在")

    sub = db.query(Subscription).filter(
        Subscription.customer_id == user_id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise HTTPException(403, "未订阅该能力，请先订阅")
    return cap, sub


@router.post("/sessions")
def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
):
    if req.cap_id not in CAPABILITY_TOOLS:
        raise HTTPException(400, f"能力 {req.cap_id} 暂不支持对话")

    db = SessionLocal()
    try:
        cap, sub = _check_subscription(db, current_user.id, req.cap_id)
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            "cap_id": req.cap_id,
            "cap_name": cap.name,
            "customer_id": current_user.id,
            "subscription_id": sub.id,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if len(_sessions) > MAX_SESSIONS:
            for sid in list(_sessions.keys())[: len(_sessions) - MAX_SESSIONS]:
                _sessions.pop(sid, None)

        return {"session_id": session_id, "cap_id": req.cap_id, "cap_name": cap.name}
    finally:
        db.close()


@router.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user)):
    return {
        "sessions": [
            {
                "session_id": sid,
                "cap_id": session["cap_id"],
                "cap_name": session["cap_name"],
                "created_at": session["created_at"],
                "message_count": len(session["messages"]),
            }
            for sid, session in _sessions.items()
            if session["customer_id"] == current_user.id
        ]
    }


@router.post("/chat")
async def chat(
    msg: ChatMessage,
    current_user: User = Depends(get_current_user),
):
    session = _sessions.get(msg.session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    if session["customer_id"] != current_user.id:
        raise HTTPException(403, "无权访问该会话")

    cap_id = session["cap_id"]
    cap_config = CAPABILITY_TOOLS.get(cap_id)
    if not cap_config:
        raise HTTPException(400, f"能力 {cap_id} 暂不支持对话")

    user_text = msg.message.strip()
    if not user_text:
        raise HTTPException(400, "消息不能为空")

    session["messages"].append({"role": "user", "content": user_text})
    if len(session["messages"]) > MAX_HISTORY * 2:
        session["messages"] = session["messages"][-MAX_HISTORY:]

    try:
        client = _get_llm()
        customer_config = get_customer_config_value(current_user.id, cap_id)
        device_id = ws_manager.get_device_for_customer(current_user.id)

        runtime_hint = "\n\n运行状态："
        runtime_hint += "客户本地客户端在线，可以执行已注册工具。" if device_id else "客户本地客户端离线，不能执行真实操作。"
        if customer_config:
            redacted = _redact_config(customer_config)
            runtime_hint += "\n客户已保存配置摘要：" + json.dumps(redacted, ensure_ascii=False)[:800]
        else:
            runtime_hint += "\n客户尚未保存该能力配置。"

        messages = [
            {"role": "system", "content": cap_config["system_prompt"] + runtime_hint},
            *session["messages"][-MAX_HISTORY:],
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=cap_config["tools"],
            tool_choice="auto",
            temperature=0.2,
            max_tokens=2048,
        )
        assistant_msg = response.choices[0].message

        if assistant_msg.tool_calls:
            messages.append(assistant_msg.model_dump(exclude_none=True))
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments or "{}")
                logger.info("Tool call: %s(%s) customer=%s", fn_name, fn_args, current_user.id)

                if device_id:
                    task_result = await ws_manager.send_task(device_id, {
                        "capability_id": cap_id,
                        "action": fn_name,
                        "params": fn_args,
                        "timeout": 30,
                    })
                else:
                    task_result = {
                        "success": False,
                        "error": "客户本地客户端离线，无法执行真实操作。请先启动 AgentHub 客户端。",
                        "data": None,
                    }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(task_result, ensure_ascii=False),
                })

            final_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
            )
            reply = final_response.choices[0].message.content or "操作已返回，但暂时无法生成摘要。"
        else:
            reply = assistant_msg.content or "我暂时无法处理这个请求。"

        session["messages"].append({"role": "assistant", "content": reply})
        return {"session_id": msg.session_id, "reply": reply, "cap_id": cap_id}

    except Exception as exc:
        logger.error("Chat engine error: %s", exc)
        raise HTTPException(500, f"对话处理失败: {str(exc)[:200]}")


def _redact_config(config: dict) -> dict:
    redacted = dict(config or {})
    for key in list(redacted.keys()):
        lowered = key.lower()
        if "password" in lowered or "secret" in lowered or "token" in lowered:
            redacted[key] = "******" if redacted[key] else ""
    return redacted
