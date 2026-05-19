"""健康监控 - 能力运行状态检测"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from ..config import (
    HEALTH_ERROR_RATE_DEGRADED, HEALTH_ERROR_RATE_DOWN,
    HEALTH_DEGRADED_THRESHOLD, HEALTH_DOWN_THRESHOLD,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL,
)

logger = logging.getLogger("agenthub.health")


class HealthMonitor:
    """能力健康监控器"""

    def __init__(self):
        self._stats = defaultdict(lambda: {
            "total": 0, "errors": 0, "timeouts": 0,
            "total_duration_ms": 0, "consecutive_degraded": 0,
        })
        self._alerted = {}  # cap_id -> bool

    def record_call(self, capability_id: int, status: str, duration_ms: int):
        """记录一次调用"""
        s = self._stats[capability_id]
        s["total"] += 1
        s["total_duration_ms"] += duration_ms
        if status in ("error", "timeout"):
            s["errors"] += 1
        if status == "timeout":
            s["timeouts"] += 1

    def get_health(self, capability_id: int) -> str:
        """
        计算能力健康状态

        Returns:
            "healthy" | "degraded" | "down"
        """
        s = self._stats.get(capability_id)
        if not s or s["total"] < 10:
            return "healthy"  # 样本不足，默认健康

        error_rate = s["errors"] / s["total"]
        avg_duration = s["total_duration_ms"] / s["total"]

        if error_rate > HEALTH_ERROR_RATE_DOWN or avg_duration > 30000:
            s["consecutive_degraded"] += 1
            if s["consecutive_degraded"] >= HEALTH_DOWN_THRESHOLD:
                return "down"
            return "degraded"

        if error_rate > HEALTH_ERROR_RATE_DEGRADED or avg_duration > 15000:
            s["consecutive_degraded"] += 1
            if s["consecutive_degraded"] >= HEALTH_DEGRADED_THRESHOLD:
                if not self._alerted.get(capability_id):
                    self._send_alert(capability_id, "degraded", error_rate)
                    self._alerted[capability_id] = True
                return "degraded"
            return "healthy"

        # 恢复正常
        s["consecutive_degraded"] = 0
        self._alerted[capability_id] = False
        return "healthy"

    def reset(self, capability_id: int):
        """重置统计"""
        self._stats.pop(capability_id, None)
        self._alerted.pop(capability_id, None)

    def _send_alert(self, capability_id: int, level: str, error_rate: float):
        """发送告警（MVP：日志，后续扩展邮件）"""
        logger.warning(
            f"⚡ Capability #{capability_id} health: {level} "
            f"(error_rate={error_rate:.1%})"
        )
        # 简化：MVP 只记录日志，后续扩展邮件
        # _send_email(f"AgentHub 告警: 能力 #{capability_id} {level}", ...)


# 全局实例
monitor = HealthMonitor()
