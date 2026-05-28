"""ISP broadband customer-service capability plugin.

This plugin talks to customer-side ISP systems from the local client. The first
real adapters are based on the customer's trained LFRADIUS and MQ-Link ITMS
flows. Write operations stay guarded until the confirmation workflow is added.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from agenthub_client import CapabilityPlugin

logger = logging.getLogger("agenthub.plugin.isp")


class ISPBroadbandPlugin(CapabilityPlugin):
    """Execute ISP customer-service actions against local customer systems."""

    cap_id = "isp-smart-cs"
    cap_name = "ISP智能客服"
    VERSION = "1.0.17"

    ACTIONS = [
        "test_connectivity",
        "query_account",
        "renew_account",
        "suspend_account",
        "reactive_account",
        "create_ticket",
        "query_onu_status",
        "reboot_onu",
    ]

    def __init__(self, config: dict):
        super().__init__(config)
        self._billing_cookies: httpx.Cookies | None = None
        self._billing_login_at = 0.0
        self._tr069_cookies = ""
        self._tr069_login_at = 0.0
        self._tr069_session: dict[str, Any] = {}
        self._load_config()

    def update_config(self, config: dict):
        super().update_config(config)
        self._load_config()
        self._billing_cookies = None
        self._billing_login_at = 0.0
        self._tr069_cookies = ""
        self._tr069_login_at = 0.0
        logger.info(
            "ISP plugin config refreshed: billing=%s tr069=%s olt=%s ticket=%s",
            bool(self.billing_url),
            bool(self.tr069_url),
            bool(self.olt_url),
            bool(self.ticket_system_url),
        )

    def _load_config(self):
        config = self.config or {}
        self.billing_url = (config.get("billing_url") or "").rstrip("/")
        self.billing_username = config.get("billing_username") or ""
        self.billing_password = config.get("billing_password") or ""
        self.billing_api_type = (config.get("billing_api_type") or "generic_rest").lower()

        self.tr069_url = (config.get("tr069_url") or "").rstrip("/")
        self.tr069_username = config.get("tr069_username") or ""
        self.tr069_password = config.get("tr069_password") or ""
        self.tr069_api_type = (config.get("tr069_api_type") or "miaokai_tr069").lower()

        self.olt_url = (config.get("olt_url") or "").rstrip("/")
        self.olt_username = config.get("olt_username") or ""
        self.olt_password = config.get("olt_password") or ""

        self.ticket_system_url = (config.get("ticket_system_url") or "").rstrip("/")
        self.ticket_username = config.get("ticket_username") or ""
        self.ticket_password = config.get("ticket_password") or ""

    async def execute(self, action: str, params: dict) -> dict:
        handler = getattr(self, f"_do_{action}", None)
        if not handler:
            return {"success": False, "error": f"不支持的操作: {action}", "data": None}
        try:
            return await handler(params or {})
        except Exception as exc:
            logger.exception("Action %s failed", action)
            return {"success": False, "error": str(exc), "data": None}

    def _effective_config(self, params: dict) -> dict:
        override = params.get("config") if isinstance(params, dict) else None
        merged = dict(self.config or {})
        if isinstance(override, dict) and override:
            merged.update(override)
        return merged

    async def _probe_http(self, name: str, base_url: str, username: str = "", password: str = "") -> dict:
        if not base_url:
            return {"name": name, "status": "skipped", "message": "未配置地址"}
        auth = (username, password) if username or password else None
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True, verify=False) as client:
                resp = await client.get(base_url.rstrip("/"), auth=auth)
            if resp.status_code < 500:
                return {"name": name, "status": "ok", "message": f"已连通，HTTP {resp.status_code}", "status_code": resp.status_code}
            return {"name": name, "status": "error", "message": f"服务端返回 HTTP {resp.status_code}", "status_code": resp.status_code}
        except Exception as exc:
            return {"name": name, "status": "error", "message": str(exc)}

    async def _do_test_connectivity(self, params: dict) -> dict:
        config = self._effective_config(params)
        checks = [
            await self._probe_http("计费系统", config.get("billing_url", ""), config.get("billing_username", ""), config.get("billing_password", "")),
            await self._probe_http("TR069/ACS", config.get("tr069_url", ""), config.get("tr069_username", ""), config.get("tr069_password", "")),
            await self._probe_http("OLT管理", config.get("olt_url", ""), config.get("olt_username", ""), config.get("olt_password", "")),
            await self._probe_http("工单系统", config.get("ticket_system_url", ""), config.get("ticket_username", ""), config.get("ticket_password", "")),
            await self._probe_http("IPTV系统", config.get("iptv_url", ""), config.get("iptv_username", ""), config.get("iptv_password", "")),
        ]
        errors = [item for item in checks if item["status"] == "error"]
        ok = [item for item in checks if item["status"] == "ok"]
        return {"success": not errors and bool(ok), "data": {"checks": checks}, "error": None if not errors else f"{len(errors)}项连通失败"}

    def _billing_base(self) -> str:
        if not self.billing_url:
            raise RuntimeError("计费系统地址未配置，请先在本地配置中填写计费系统信息。")
        base = self.billing_url.rstrip("/")
        if base.endswith("/control.php"):
            return base
        if "/lfradius" in base:
            return f"{base}/control.php" if not base.endswith("/lfradius") else f"{base}/control.php"
        return f"{base}/lfradius/control.php"

    def _tr069_base(self) -> str:
        if not self.tr069_url:
            raise RuntimeError("TR069系统地址未配置，请先在本地配置中填写TR069系统信息。")
        parts = urlsplit(self.tr069_url.rstrip("/"))
        return urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")

    async def _lfradius_request(self, query: dict[str, Any], method: str = "GET", body: dict[str, Any] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
            if self._billing_cookies:
                client.cookies = self._billing_cookies
            if method.upper() == "POST":
                resp = await client.post(self._billing_base(), params=query, data=body or {})
            else:
                resp = await client.get(self._billing_base(), params=query)
            self._billing_cookies = client.cookies
            resp.raise_for_status()
            return resp.json()

    async def _ensure_lfradius_login(self):
        if self._billing_login_at and time.time() - self._billing_login_at < 25 * 60 and self._billing_cookies:
            return
        if not self.billing_username or not self.billing_password:
            raise RuntimeError("计费系统账号或密码未配置。")
        result = await self._lfradius_request(
            {"c": "login", "a": "admin_login"},
            "POST",
            {"username": self.billing_username, "password": self.billing_password},
        )
        if result.get("v", {}).get("success") != 1:
            raise RuntimeError(result.get("v", {}).get("msg") or "凌风计费系统登录失败")
        self._billing_login_at = time.time()

    async def _lfradius_user_list(self, params: dict[str, Any]) -> dict:
        await self._ensure_lfradius_login()
        result = await self._lfradius_request({"c": "user", "a": "user_list", **params}, "POST", params)
        if result.get("v", {}).get("success") == 1:
            data = result.get("d") or {}
            return {
                "success": True,
                "users": data.get("user") or [],
                "total": data.get("total") or 0,
                "count": len(data.get("user") or []),
                "raw": result,
            }
        return {"success": False, "users": [], "total": 0, "count": 0, "error": result.get("v", {}).get("msg") or "查询失败", "raw": result}

    async def _lfradius_search_user(self, keyword: str) -> dict:
        kw = (keyword or "").strip()
        search = {
            "page": 1,
            "pagesize": 100,
            "search_key": kw,
            "search_method": "vague",
            "iffirstlogin": "",
            "groupid": "",
            "groupminid": "",
            "group3id": "",
            "serverid": "",
            "admin": "",
            "pause": "",
            "reserved_number": "",
            "registrtime_starttime": "",
            "registrtime_stoptime": "",
            "expiretime_starttime": "",
            "expiretime_stoptime": "",
            "search_batch_key": "",
            "orderby": "",
        }
        fields = [
            "user", "presentaddress", "phone", "log", "name", "certnum", "staticip",
            "staticmac", "portid", "servername", "nasip", "nasid", "loid", "box",
            "port", "vlanid", "vlansn", "pass", "proxy_vlan", "proxy_user", "proxy_pass",
        ]
        for idx, field in enumerate(fields):
            search[f"search_type[{idx}]"] = field
        return await self._lfradius_user_list(search)

    async def _lfradius_user_detail(self, user_id: str | int) -> dict:
        await self._ensure_lfradius_login()
        result = await self._lfradius_request({"c": "user", "a": "user_edit", "id": user_id})
        if result.get("v", {}).get("success") == 1:
            return {"success": True, "user": (result.get("d") or {}).get("user") or {}, "raw": result}
        return {"success": False, "error": result.get("v", {}).get("msg") or "获取用户详情失败", "raw": result}

    async def _lfradius_query_account(self, account: str, query_type: str = "status") -> dict:
        found = await self._lfradius_search_user(account)
        if not found.get("success") or not found.get("users"):
            return {"success": False, "error": f"未找到账号：{account}", "data": {"account": account, "matches": []}}

        users = found["users"][:5]
        summaries = []
        for user in users:
            detail_user = user
            if user.get("id"):
                detail = await self._lfradius_user_detail(user["id"])
                if detail.get("success") and detail.get("user"):
                    detail_user = {**user, **detail["user"]}
            summaries.append(self._normalize_billing_user(detail_user))

        return {
            "success": True,
            "data": {
                "adapter": "lfradius",
                "query_type": query_type,
                "keyword": account,
                "count": found.get("count", len(summaries)),
                "users": summaries,
            },
        }

    def _normalize_billing_user(self, user: dict[str, Any]) -> dict:
        online_value = str(user.get("online") or user.get("ifonline") or user.get("state") or "")
        pause_value = str(user.get("pause") or user.get("disabled") or "")
        return {
            "id": user.get("id"),
            "account": user.get("user") or user.get("username") or user.get("account"),
            "name": user.get("name") or user.get("realname") or "",
            "phone": user.get("phone") or user.get("mobile") or "",
            "package": user.get("serverid_name") or user.get("servername") or "",
            "online": online_value in {"1", "online", "true", "True"},
            "paused": pause_value in {"1", "true", "True"},
            "expire_time": user.get("expiretime") or user.get("stoptime") or "",
            "address": user.get("presentaddress") or user.get("address") or "",
            "last_login": user.get("lastlogin") or user.get("lastlogintime") or "",
            "nas": user.get("nasip") or user.get("nasid") or "",
            "loid": user.get("loid") or "",
            "raw": user,
        }

    async def _generic_billing_request(self, method: str, path: str, json_data: dict | None = None) -> dict:
        if not self.billing_url:
            raise RuntimeError("计费系统地址未配置，请先在本地配置中填写计费系统信息。")
        url = f"{self.billing_url}{path}"
        auth = (self.billing_username, self.billing_password)
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            if method == "GET":
                resp = await client.get(url, auth=auth, params=json_data)
            else:
                resp = await client.post(url, auth=auth, json=json_data)
            resp.raise_for_status()
            return resp.json()

    async def _do_query_account(self, params: dict) -> dict:
        account = params.get("account") or params.get("keyword") or params.get("user") or ""
        query_type = params.get("query_type", "status")
        if not account:
            return {"success": False, "error": "缺少要查询的账号、手机号或关键字", "data": None}
        if self.billing_api_type in {"lingfeng", "lfradius", "lingfeng_lfradius"}:
            return await self._lfradius_query_account(account, query_type)
        result = await self._generic_billing_request("GET", "/api/account/query", {"account": account, "type": query_type})
        return {"success": True, "data": result}

    async def _do_renew_account(self, params: dict) -> dict:
        return {"success": False, "error": "续费属于写操作，本版本已接入查询链路，需增加二次确认后再开放。", "data": None}

    async def _do_suspend_account(self, params: dict) -> dict:
        return {"success": False, "error": "停机属于写操作，需增加二次确认和审计后再开放。", "data": None}

    async def _do_reactive_account(self, params: dict) -> dict:
        return {"success": False, "error": "复机属于写操作，需增加二次确认和审计后再开放。", "data": None}

    async def _do_create_ticket(self, params: dict) -> dict:
        payload = {
            "account": params.get("account", ""),
            "issue_type": params.get("issue_type", "other"),
            "description": params.get("description", ""),
            "contact_phone": params.get("contact_phone", ""),
        }
        if not self.ticket_system_url:
            return {"success": False, "error": "工单系统暂未配置；如果客户没有独立工单系统，后续可接入平台内置工单。", "data": payload}
        auth = (self.ticket_username, self.ticket_password)
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.post(f"{self.ticket_system_url}/api/tickets", auth=auth, json=payload)
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}

    async def _tr069_login_mq_link(self):
        if self._tr069_login_at and time.time() - self._tr069_login_at < 25 * 60 and self._tr069_cookies:
            return
        if not self.tr069_url or not self.tr069_username or not self.tr069_password:
            raise RuntimeError("TR069系统地址、账号或密码未配置。")
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            base = self._tr069_base()
            vcode_resp = await client.get(f"{base}/api/vcode", params={"format": "base64", "lang": "zh_CN"})
            vcode_resp.raise_for_status()
            ip = (vcode_resp.json() or {}).get("ip") or "127.0.0.1"
            double_md5 = hashlib.md5(hashlib.md5(self.tr069_password.encode()).hexdigest().encode()).hexdigest()
            passwd = hashlib.md5(f"{ip} {double_md5} ".encode()).hexdigest()
            login_resp = await client.post(
                f"{base}/api/login",
                data={
                    "uid": self.tr069_username,
                    "passwd": passwd,
                    "save_login": "false",
                    "vcode": "",
                    "from": "",
                    "ip": ip,
                },
            )
            login_resp.raise_for_status()
            result = login_resp.json()
            if result.get("code") != 1:
                raise RuntimeError(f"TR069登录失败：{result.get('result') or result}")
            self._tr069_session = result
            self._tr069_cookies = (
                f"uid={result.get('uid')}; mid={result.get('mid')}; login_level={result.get('level')}; "
                f"TM_OFFSET_=0; sysauth={result.get('sid')}; LOGIN_TIME={result.get('login_time')}"
            )
            self._tr069_login_at = time.time()

    @staticmethod
    def _parse_jsonp(body: str) -> dict:
        match = re.match(r"^\w+\(([\s\S]*)\)$", body.strip())
        if match:
            return httpx.Response(200, text=match.group(1)).json()
        return httpx.Response(200, text=body).json()

    async def _mq_link_call(self, operation: str, extra: dict[str, Any] | None = None) -> dict:
        await self._tr069_login_mq_link()
        params = {"o": operation, "_lang": "zh_CN", **(extra or {})}
        headers = {"Cookie": self._tr069_cookies, "X-Requested-With": "XMLHttpRequest"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
            resp = await client.post(f"{self._tr069_base()}/api/post_tr069?jsonpcallback=cb", data=params, headers=headers)
            resp.raise_for_status()
            if "window.location" in resp.text:
                self._tr069_cookies = ""
                self._tr069_login_at = 0.0
                return await self._mq_link_call(operation, extra)
            return self._parse_jsonp(resp.text)

    async def _mq_link_device_summary(self, keyword: str) -> dict:
        data = await self._mq_link_call("stat", {"page": 1, "pmax": 50, "k": keyword, "sort": "", "rsort": "", "cursor": ""})
        devices = data.get("data") or []
        if not devices:
            return {"found": False, "keyword": keyword, "message": f"未找到匹配 {keyword} 的光猫"}
        device = devices[0]
        wan = {}
        uuid = device.get("uuid")
        if uuid:
            try:
                wan_result = await self._mq_link_call("get_wan", {"target": uuid})
                wan = {"items": wan_result.get("data") or []}
            except Exception as exc:
                wan = {"error": str(exc)}
        return {
            "found": True,
            "keyword": keyword,
            "uuid": uuid,
            "sn": device.get("serialnumber"),
            "mac": device.get("macaddress"),
            "model": device.get("devicetype"),
            "manufacturer": device.get("manufacturer"),
            "online": str(device.get("status")) == "1",
            "optical": {
                "rx_power": device.get("RXPower"),
                "tx_power": device.get("TXPower"),
                "temperature": device.get("TransceiverTemperature"),
                "bias_current": device.get("BiasCurrent"),
                "voltage": device.get("SupplyVottage"),
            },
            "pppoe": {
                "user": device.get("pppoeuser"),
                "status": device.get("ppp_stat"),
                "error": device.get("ppp_err"),
            },
            "wan": wan,
            "raw": device,
        }

    async def _do_query_onu_status(self, params: dict) -> dict:
        keyword = params.get("account") or params.get("keyword") or params.get("sn") or params.get("mac") or ""
        if not keyword:
            return {"success": False, "error": "缺少要查询的账号、SN或MAC", "data": None}
        if self.tr069_api_type in {"miaokai_tr069", "mq_link", "irouter_itms"}:
            summary = await self._mq_link_device_summary(keyword)
            return {"success": bool(summary.get("found")), "data": summary, "error": None if summary.get("found") else summary.get("message")}
        result = await self._generic_billing_request("GET", "/api/onu/status", {"account": keyword})
        return {"success": True, "data": result}

    async def _do_reboot_onu(self, params: dict) -> dict:
        return {"success": False, "error": "重启光猫属于写操作，需增加二次确认和审计后再开放。", "data": None}
