"""对话引擎 - LLM Function Calling + 工具执行

MVP 简化版，后续集成完整 DeepSeek Function Calling。
"""

import json
import logging
from typing import Optional
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, MAX_TOOL_CALL_ROUNDS

logger = logging.getLogger("agenthub.chat_engine")


def process_message(message: str, capability, context: list,
                    allowed_tools: list = None,
                    customer_config: dict = None) -> dict:
    """
    处理用户消息，返回 LLM 回复或工具执行指令

    Args:
        message: 用户消息
        capability: Capability 对象
        context: 对话上下文
        allowed_tools: 桥接模式下的允许工具白名单
        customer_config: 客户配置（环境变量）

    Returns:
        {"type": "final_reply", "content": "..."}
        {"type": "tool_call", "tool_id": "...", "tool_name": "...", "params": {...}}
    """

    # MVP 简化版：关键词匹配
    # 完整版会集成 DeepSeek Function Calling
    if DEEPSEEK_API_KEY:
        return _call_llm(message, capability, context, allowed_tools, customer_config)

    # 无 LLM Key 时的 fallback 回复
    return _simple_reply(message, capability)


def _call_llm(message, capability, context, allowed_tools, customer_config) -> dict:
    """调用 DeepSeek API 处理"""
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        # 构建 system prompt
        system_parts = []
        # 从能力包加载 SOUL.md（这里简化为从数据库的 runtime_config 读取）
        soul_text = "你是一个专业的AI助手，根据提供的信息和工具来帮助用户解决问题。"
        if capability.long_description:
            soul_text += f"\n\n## 能力描述\n{capability.long_description}"

        system_parts.append({"role": "system", "content": soul_text})

        # 构建消息列表
        messages = system_parts + context[-10:]  # 最多保留最近 10 轮

        # 构建工具定义（从能力包的 tools 信息获取）
        # MVP 简化：使用内置工具
        tools = _get_tool_definitions(allowed_tools)

        # 调用 DeepSeek
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            tools=tools if tools else None,
            temperature=0.3,
            max_tokens=2000,
        )

        choice = response.choices[0]
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # LLM 请求执行工具
            tool_call = choice.message.tool_calls[0]
            return {
                "type": "tool_call",
                "tool_id": tool_call.id,
                "tool_name": tool_call.function.name,
                "params": json.loads(tool_call.function.arguments),
            }
        else:
            # LLM 返回普通文本回复
            return {
                "type": "final_reply",
                "content": choice.message.content or "处理完成",
            }

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "type": "final_reply",
            "content": f"AI 处理出错: {str(e)}",
        }


def _get_tool_definitions(allowed_tools: list = None) -> list:
    """获取 LLM 工具定义"""
    all_tools = {
        "ssh_execute": {
            "type": "function",
            "function": {
                "name": "ssh_execute",
                "description": "通过 SSH 执行远程命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "设备 IP"},
                        "port": {"type": "integer", "description": "SSH 端口"},
                        "username": {"type": "string", "description": "登录用户名"},
                        "password": {"type": "string", "description": "登录密码"},
                        "command": {"type": "string", "description": "要执行的命令"},
                    },
                    "required": ["host", "username", "password", "command"],
                },
            },
        },
        "snmp_get": {
            "type": "function",
            "function": {
                "name": "snmp_get",
                "description": "SNMP 获取设备信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "设备 IP"},
                        "community": {"type": "string", "description": "SNMP community"},
                        "oids": {"type": "array", "items": {"type": "string"}, "description": "OID 列表"},
                    },
                    "required": ["host", "community", "oids"],
                },
            },
        },
        "http_request": {
            "type": "function",
            "function": {
                "name": "http_request",
                "description": "发送 HTTP 请求",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "enum": ["GET", "POST"]},
                        "headers": {"type": "object"},
                        "body": {"type": "string"},
                    },
                    "required": ["url", "method"],
                },
            },
        },
        "ping_check": {
            "type": "function",
            "function": {
                "name": "ping_check",
                "description": "Ping 检测设备是否在线",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "设备 IP"},
                        "count": {"type": "integer", "description": "Ping 次数"},
                    },
                    "required": ["host"],
                },
            },
        },
    }

    if allowed_tools:
        return [v for k, v in all_tools.items() if k in allowed_tools]
    return list(all_tools.values())


def _simple_reply(message: str, capability) -> dict:
    """无 LLM 时的简单回复"""
    # 关键词匹配
    keywords = {
        "帮助": f"我是 {capability.name}，可以帮你完成相关操作。请问有什么具体需要？",
        "你好": f"你好！我是 {capability.name}，有什么可以帮你的？",
    }
    for kw, reply in keywords.items():
        if kw in message:
            return {"type": "final_reply", "content": reply}

    return {
        "type": "final_reply",
        "content": f"已收到您的请求，正在使用 {capability.name} 处理。如需进一步支持，请详细描述您的问题。",
    }
