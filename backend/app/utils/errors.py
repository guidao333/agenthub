"""统一错误码体系"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorInfo:
    code: str
    http_status: int
    message: str


class ErrorCode:
    # ========== 认证 (1xxx) ==========
    AUTH_INVALID_CREDENTIALS = ErrorInfo("AUTH_1001", 401, "用户名或密码错误")
    AUTH_TOKEN_EXPIRED = ErrorInfo("AUTH_1002", 401, "登录已过期，请重新登录")
    AUTH_PERMISSION_DENIED = ErrorInfo("AUTH_1003", 403, "权限不足")
    AUTH_API_KEY_INVALID = ErrorInfo("AUTH_1004", 401, "API Key 无效")
    AUTH_API_KEY_EXPIRED = ErrorInfo("AUTH_1005", 401, "API Key 已过期")
    AUTH_USER_DISABLED = ErrorInfo("AUTH_1006", 403, "账号已被禁用")
    AUTH_USERNAME_TAKEN = ErrorInfo("AUTH_1007", 409, "用户名已被注册")
    AUTH_EMAIL_TAKEN = ErrorInfo("AUTH_1008", 409, "邮箱已被注册")

    # ========== 计费 (2xxx) ==========
    BILL_INSUFFICIENT_BALANCE = ErrorInfo("BILL_2001", 402, "余额不足，请先充值")
    BILL_FROZEN_CONFLICT = ErrorInfo("BILL_2002", 409, "余额操作冲突，请稍后重试")
    BILL_REFUND_PENDING = ErrorInfo("BILL_2003", 202, "退款申请已提交")
    BILL_INVALID_AMOUNT = ErrorInfo("BILL_2004", 400, "金额无效")
    BILL_MIN_WITHDRAW = ErrorInfo("BILL_2005", 400, "可提现余额不足 100 元")

    # ========== 能力 (3xxx) ==========
    CAP_NOT_FOUND = ErrorInfo("CAP_3001", 404, "能力不存在")
    CAP_NOT_SUBSCRIBED = ErrorInfo("CAP_3002", 403, "未订阅该能力")
    CAP_NOT_AVAILABLE = ErrorInfo("CAP_3003", 503, "能力暂时不可用")
    CAP_VERSION_MISMATCH = ErrorInfo("CAP_3004", 409, "能力版本不匹配")
    CAP_DEPENDENCY_MISSING = ErrorInfo("CAP_3005", 422, "依赖能力未订阅")
    CAP_DUPLICATE_ID = ErrorInfo("CAP_3006", 409, "能力 ID 已被使用")
    CAP_CANNOT_MODIFY = ErrorInfo("CAP_3007", 403, "当前状态不允许修改")
    CAP_TRIAL_EXHAUSTED = ErrorInfo("CAP_3008", 429, "今日试用次数已用完")
    CAP_REVIEW_FAILED = ErrorInfo("CAP_3009", 422, "能力包审核未通过")
    CAP_LOAD_FAILED = ErrorInfo("CAP_3010", 500, "能力包加载失败")

    # ========== 调用 (4xxx) ==========
    CALL_TIMEOUT = ErrorInfo("CALL_4001", 504, "能力执行超时")
    CALL_TOOL_ERROR = ErrorInfo("CALL_4002", 500, "工具执行失败")
    CALL_LLM_ERROR = ErrorInfo("CALL_4003", 502, "AI 模型调用失败")
    CALL_RATE_LIMIT = ErrorInfo("CALL_4004", 429, "调用频率超限，请稍后重试")
    CALL_INVALID_PARAMS = ErrorInfo("CALL_4005", 400, "参数验证失败")
    CALL_INTERNAL_ERROR = ErrorInfo("CALL_4006", 500, "能力内部错误")

    # ========== 桥接 (5xxx) ==========
    BRIDGE_SESSION_EXPIRED = ErrorInfo("BR_5001", 410, "桥接会话已过期，请重新连接")
    BRIDGE_EXEC_FAILED = ErrorInfo("BR_5002", 500, "本地执行失败")
    BRIDGE_TOOL_DENIED = ErrorInfo("BR_5003", 403, "该操作不在客户允许的范围内")
    BRIDGE_CONNECTION_LOST = ErrorInfo("BR_5004", 504, "桥接连接中断")
    BRIDGE_SESSION_NOT_FOUND = ErrorInfo("BR_5005", 404, "桥接会话不存在")

    # ========== 开发者 (6xxx) ==========
    DEV_CAP_DUPLICATE = ErrorInfo("DEV_6001", 409, "能力 ID 已存在")
    DEV_CAP_VALIDATION_FAILED = ErrorInfo("DEV_6002", 422, "能力包格式校验失败")
    DEV_TEST_FAILED = ErrorInfo("DEV_6003", 422, "测试用例未通过")
    DEV_WITHDRAW_MIN = ErrorInfo("DEV_6004", 400, "可提现余额需不低于 100 元")
    DEV_CONFIG_ERROR = ErrorInfo("DEV_6005", 400, "能力配置错误")

    # ========== 管理 (7xxx) ==========
    ADMIN_REVIEW_EXISTS = ErrorInfo("ADM_7001", 409, "该能力已有审核中的申请")
    ADMIN_USER_NOT_FOUND = ErrorInfo("ADM_7002", 404, "用户不存在")
    ADMIN_PRICE_INVALID = ErrorInfo("ADM_7003", 400, "定价无效")
    ADMIN_OPERATION_FAILED = ErrorInfo("ADM_7004", 500, "操作执行失败")

    # ========== 通用 (9xxx) ==========
    COMMON_NOT_FOUND = ErrorInfo("COMM_9001", 404, "资源不存在")
    COMMON_INVALID_REQUEST = ErrorInfo("COMM_9002", 400, "请求参数无效")
    COMMON_INTERNAL_ERROR = ErrorInfo("COMM_9003", 500, "服务器内部错误")
    COMMON_SERVICE_UNAVAILABLE = ErrorInfo("COMM_9004", 503, "服务暂时不可用")


def api_response(success: bool = True, data: dict = None, error: ErrorInfo = None,
                 detail: str = None, trace_id: str = None) -> dict:
    """统一 API 响应格式"""
    resp = {"success": success, "data": data or {}}
    if error:
        resp["error"] = {
            "code": error.code,
            "message": error.message,
            "detail": detail,
            "doc_url": f"https://www.agenthub.wang/docs/errors/{error.code}",
        }
    resp["meta"] = {
        "request_id": trace_id or "",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    return resp


class AppException(Exception):
    """业务异常，会由全局处理器捕获并返回统一格式"""
    def __init__(self, error: ErrorInfo, detail: str = None, trace_id: str = None):
        self.error = error
        self.detail = detail
        self.trace_id = trace_id
        super().__init__(error.message)

    def to_response(self):
        return api_response(success=False, error=self.error, detail=self.detail)
