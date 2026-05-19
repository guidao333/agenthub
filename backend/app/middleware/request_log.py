"""请求日志和 trace_id 注入"""

import time
import logging
from uuid import uuid4
from fastapi import Request, Response

logger = logging.getLogger("agenthub.access")


async def request_logging(request: Request, call_next):
    """注入 trace_id 并记录请求日志"""
    trace_id = getattr(request.state, "trace_id", f"req_{uuid4().hex[:16]}")
    request.state.trace_id = trace_id
    request.state.start_time = time.time()

    response: Response = await call_next(request)

    duration = int((time.time() - request.state.start_time) * 1000)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration}ms) "
        f"[{trace_id}]"
    )

    return response
