"""通用工具函数"""

import uuid
import json
from datetime import datetime, timezone, timedelta

# Asia/Shanghai
SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


def now_str() -> str:
    """返回上海时间的 ISO 格式字符串"""
    return datetime.now(SHANGHAI).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def now_timestamp() -> str:
    """返回上海时间的紧凑格式"""
    return datetime.now(SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")


def new_trace_id() -> str:
    """生成调用链追踪 ID"""
    return f"trc_{uuid.uuid4().hex[:24]}"


def new_request_id() -> str:
    """生成请求 ID"""
    return f"req_{uuid.uuid4().hex[:16]}"


def new_api_key() -> str:
    """生成 API Key"""
    return f"cus_{uuid.uuid4().hex[:24]}"


def new_session_id() -> str:
    """生成会话 ID"""
    return uuid.uuid4().hex


def parse_json_field(value: str, default=None):
    """安全解析 JSON 字段"""
    if not value:
        return default or {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default or {}


def serialize_json(data) -> str:
    """序列化为 JSON 字符串"""
    return json.dumps(data, ensure_ascii=False)
