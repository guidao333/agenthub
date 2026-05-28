"""AI monitor capability plugin."""

import logging
from urllib.parse import urlparse

from agenthub_client import CapabilityPlugin

logger = logging.getLogger("agenthub.plugin.vision")


class VisionPlugin(CapabilityPlugin):
    cap_id = "ai-smart-monitor"
    cap_name = "AI 智能监控"
    VERSION = "0.1.0"

    ACTIONS = ["test_connectivity", "list_sources", "query_recording", "search_person", "configure_notification"]

    def update_config(self, config: dict):
        super().update_config(config)
        logger.info(
            "Vision plugin config refreshed: nvr=%s rtsp=%s notifications=%s",
            bool(self.config.get("nvr_url")),
            bool(self.config.get("rtsp_base_url")),
            bool(self._notification_channels()),
        )

    async def execute(self, action: str, params: dict) -> dict:
        handler = getattr(self, f"_do_{action}", None)
        if not handler:
            return {"success": False, "error": f"不支持的操作: {action}", "data": None}
        return await handler(params or {})

    def _effective_config(self, params: dict) -> dict:
        merged = dict(self.config or {})
        override = params.get("config") if isinstance(params, dict) else None
        if isinstance(override, dict):
            merged.update(override)
        return merged

    def _notification_channels(self, config: dict | None = None) -> list[str]:
        data = config or self.config or {}
        channels = []
        for key, label in [
            ("notify_wechat_webhook", "微信"),
            ("notify_feishu_webhook", "飞书"),
            ("notify_email", "邮件"),
            ("notify_sms_phone", "短信"),
        ]:
            if data.get(key):
                channels.append(label)
        return channels

    async def _do_test_connectivity(self, params: dict) -> dict:
        config = self._effective_config(params)
        checks = []
        for key, label in [("nvr_url", "NVR"), ("rtsp_base_url", "RTSP")]:
            value = (config.get(key) or "").strip()
            if not value:
                checks.append({"name": label, "status": "skipped", "message": "未配置地址"})
                continue
            parsed = urlparse(value)
            ok = bool(parsed.scheme and parsed.netloc)
            checks.append({"name": label, "status": "ok" if ok else "error", "message": "地址格式有效" if ok else "地址格式无效"})

        channels = self._notification_channels(config)
        checks.append({"name": "通知通道", "status": "ok" if channels else "skipped", "message": "、".join(channels) if channels else "未配置通知通道"})
        errors = [item for item in checks if item["status"] == "error"]
        return {"success": not errors, "data": {"checks": checks}, "error": None if not errors else f"{len(errors)} 项配置格式异常"}

    async def _do_list_sources(self, params: dict) -> dict:
        config = self._effective_config(params)
        return {"success": True, "data": {"sources": config.get("camera_channels") or []}}

    async def _do_query_recording(self, params: dict) -> dict:
        return {"success": False, "error": "录像回查适配器待接入具体 NVR 品牌 SDK/API 后启用。", "data": {"requested": params}}

    async def _do_search_person(self, params: dict) -> dict:
        return {"success": False, "error": "AI 找人属于录像回查能力的一类，待视觉检索模型和 NVR 回放适配完成后启用。", "data": {"requested": params}}

    async def _do_configure_notification(self, params: dict) -> dict:
        return {"success": True, "data": {"channels": self._notification_channels(self._effective_config(params))}}
