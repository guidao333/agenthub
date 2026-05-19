"""统一错误处理中间件"""

import traceback
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from ..utils.errors import AppException, ErrorCode, api_response

logger = logging.getLogger("agenthub.error")


async def error_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    trace_id = getattr(request.state, "trace_id", "")

    if isinstance(exc, AppException):
        logger.warning(f"AppException [{exc.error.code}]: {exc.detail or exc.error.message}")
        return JSONResponse(
            status_code=exc.error.http_status,
            content=api_response(
                success=False,
                error=exc.error,
                detail=exc.detail,
                trace_id=trace_id,
            ),
        )

    if isinstance(exc, Exception):
        logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content=api_response(
                success=False,
                error=ErrorCode.COMMON_INTERNAL_ERROR,
                detail=str(exc)[:200] if str(exc) else None,
                trace_id=trace_id,
            ),
        )

    return JSONResponse(
        status_code=500,
        content=api_response(
            success=False,
            error=ErrorCode.COMMON_INTERNAL_ERROR,
            trace_id=trace_id,
        ),
    )
