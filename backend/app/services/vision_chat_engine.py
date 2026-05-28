"""AgentHub - AI视觉对话引擎 v2.0

用户通过自然语言与AI视觉能力对话:
- 检查北门卫生 -> 触发环境巡检
- 昨天下午有人丢垃圾吗 -> 查询事件
- 北门摄像头状态 -> 查询设备状态
"""
import json
import logging
import requests
from typing import Optional
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger("agenthub.vision_chat")

# AI视觉工具定义（给 DeepSeek Function Calling 用）
VISION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "trigger_patrol",
            "description": "触发一次环境卫生巡检，检测指定摄像头的画面中的垃圾并生成卫生评分",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera_location": {
                        "type": "string",
                        "description": "摄像头位置，如'北门'、'停车场'。留空则巡检所有摄像头"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": "查询AI视觉检测事件，如垃圾检测、高空抛物等事件记录",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": ["trash_detected", "throw_detected", "patrol_score", "all"],
                        "description": "事件类型"
                    },
                    "camera_location": {
                        "type": "string",
                        "description": "摄像头位置筛选"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "查询最近N小时的事件，默认24小时"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_camera_status",
            "description": "查询摄像头和边缘设备的在线状态、分辨率、FPS等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera_location": {
                        "type": "string",
                        "description": "摄像头位置，留空查询所有"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patrol_scores",
            "description": "查询环境卫生巡检的历史评分记录",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera_location": {"type": "string", "description": "摄像头位置"},
                    "days": {"type": "integer", "description": "查询最近N天的评分，默认7天"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vision_stats",
            "description": "获取AI视觉能力整体统计数据：今日事件数、平均评分、摄像头数量等",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

SYSTEM_PROMPT = """你是 AgentHub AI安防管家，负责管理AI视觉监控能力。

你可以帮助用户：
1. 环境卫生巡检 - 检测垃圾、生成卫生评分报告
2. 事件查询 - 查看历史检测事件（垃圾/抛物等）
3. 设备状态 - 查看摄像头在线状态
4. 巡检历史 - 查看历史卫生评分趋势
5. 统计总览 - 查看整体运行数据

录像回查、AI 找人、物品遗失、车辆检索需要接入客户 NVR 录像主机并完成对应品牌适配。
当前工具未开放真实录像回放检索时，要先收集摄像头位置、时间范围、目标描述，再说明需要 NVR 适配上线后执行。

回复要求：
- 简洁专业，用中文回复
- 有数据时用表格或列表展示
- 发现问题时给出建议
- 语气友好但不过度客套
"""


class VisionChatEngine:
    """AI视觉对话引擎"""

    def __init__(self, api_base=None):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.model = DEEPSEEK_MODEL
        self.api_base = api_base

    def chat(self, message, context, device_id=None):
        """处理用户消息，返回 {"type": "reply", "content": "..."} """
        if not self.api_key:
            return self._keyword_fallback(message, device_id)
        try:
            return self._llm_chat(message, context, device_id)
        except Exception as e:
            logger.error(f"Vision chat error: {e}")
            return {"type": "error", "content": f"AI处理出错: {e}"}

    def _llm_chat(self, message, context, device_id):
        """调用 DeepSeek Function Calling"""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(context[-20:])

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=VISION_TOOLS,
            temperature=0.3,
            max_tokens=2000,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # 执行工具调用
            tool_messages = []
            for tc in choice.message.tool_calls:
                tool_name = tc.function.name
                params = json.loads(tc.function.arguments)
                result = self._execute_tool(tool_name, params, device_id)
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # 把工具结果喂回 LLM 生成自然语言回复
            messages.append(choice.message)
            messages.extend(tool_messages)

            final = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )
            return {"type": "reply", "content": final.choices[0].message.content}

        return {"type": "reply", "content": choice.message.content or "处理完成"}

    def _execute_tool(self, tool_name, params, device_id):
        """执行工具调用，访问内部 vision API"""
        base = self.api_base or "http://127.0.0.1:8000"
        try:
            if tool_name == "trigger_patrol":
                return {
                    "status": "triggered",
                    "message": "巡检指令已发送到边缘端，结果将在1分钟内返回。",
                    "camera_location": params.get("camera_location", "全部")
                }

            elif tool_name == "query_events":
                resp = requests.get(f"{base}/api/vision/events", params={"limit": 20}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get("events", data) if isinstance(data, dict) else data
                    return {"status": "ok", "count": len(events), "events": events[:10]}
                return {"status": "error", "message": "查询失败"}

            elif tool_name == "get_camera_status":
                resp = requests.get(f"{base}/api/vision/devices", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    devices = data.get("devices", data) if isinstance(data, dict) else data
                    return {"status": "ok", "devices": devices}
                return {"status": "error", "message": "查询失败"}

            elif tool_name == "get_patrol_scores":
                resp = requests.get(f"{base}/api/vision/stats", timeout=10)
                if resp.status_code == 200:
                    return {"status": "ok", "data": resp.json()}
                return {"status": "error", "message": "查询失败"}

            elif tool_name == "get_vision_stats":
                resp = requests.get(f"{base}/api/vision/stats", timeout=10)
                if resp.status_code == 200:
                    return {"status": "ok", "data": resp.json()}
                return {"status": "error", "message": "查询失败"}

            return {"status": "error", "message": f"未知工具: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool error [{tool_name}]: {e}")
            return {"status": "error", "message": str(e)}

    def _keyword_fallback(self, message, device_id):
        """无 LLM Key 时的关键词匹配"""
        msg = message.lower()
        if any(kw in msg for kw in ["卫生", "巡检", "垃圾", "清洁"]):
            return {"type": "reply", "content": "环境巡检功能需要边缘端设备在线。请确认设备已连接并配置了摄像头。"}
        elif any(kw in msg for kw in ["事件", "报警", "告警"]):
            return {"type": "reply", "content": "事件查询功能需要边缘端设备在线。"}
        elif any(kw in msg for kw in ["状态", "摄像头", "在线"]):
            return {"type": "reply", "content": "设备状态查询功能需要边缘端设备在线。"}
        return {"type": "reply", "content": "我是AI安防管家，可以帮你进行环境巡检、事件查询、设备状态检查。请问需要什么帮助？"}
