"""API 限频中间件"""

import time
import logging
from collections import defaultdict
from fastapi import Request, Response
from ..utils.errors import ErrorCode, AppException

logger = logging.getLogger("agenthub.ratelimit")


class RateLimiter:
    """简单内存限频器"""

    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._records: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window
        # 清理窗口外记录
        self._records[key] = [t for t in self._records[key] if t > window_start]
        if len(self._records[key]) >= self.limit:
            return False
        self._records[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        now = time.time()
        window_start = now - self.window
        recent = len([t for t in self._records[key] if t > window_start])
        return max(0, self.limit - recent)


# 全局实例
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """基于 IP + API Key 的限频"""
    # 跳过内部健康检查
    if request.url.path in ("/", "/health", "/docs", "/openapi.json"):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key", "")
    client_ip = request.client.host if request.client else "unknown"
    limit_key = f"{client_ip}:{api_key[:8] if api_key else 'anon'}"

    if not rate_limiter.check(limit_key):
        raise AppException(ErrorCode.CALL_RATE_LIMIT)

    response: Response = await call_next(request)
    remaining = rate_limiter.get_remaining(limit_key)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
