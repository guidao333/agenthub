"""AgentHub client runtime.

The client keeps a WebSocket connection to AgentHub, receives structured tasks,
dispatches them to local capability plugins, and sends execution results back.
"""

import asyncio
import json
import logging
import platform
import time
from typing import Dict, Optional

import websockets

logger = logging.getLogger("agenthub.client")

CLIENT_VERSION = "1.0.17"


class CapabilityPlugin:
    """Base class for local capability plugins."""

    cap_id: str = ""
    cap_name: str = ""
    ACTIONS: list[str] = []

    def __init__(self, config: dict):
        self.config = config or {}

    def update_config(self, config: dict):
        self.config = config or {}

    async def execute(self, action: str, params: dict) -> dict:
        raise NotImplementedError(f"Action '{action}' not implemented in {self.__class__.__name__}")


class AgentHubClient:
    """Unified AgentHub desktop client."""

    def __init__(
        self,
        api_key: str = "",
        server_url: str = "wss://www.agenthub.wang",
        heartbeat_interval: int = 30,
        capability_api_keys: Optional[dict] = None,
    ):
        self.capability_api_keys = capability_api_keys or {}
        self.api_key = api_key or self._first_capability_api_key()
        self.server_url = server_url.rstrip("/")
        self.ws_url = self._build_ws_url()
        self.heartbeat_interval = heartbeat_interval

        self._plugins: Dict[str, CapabilityPlugin] = {}
        self._configs: Dict[str, dict] = {}
        self._device_id: Optional[str] = None
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._connected_at: Optional[float] = None
        self._last_heartbeat_ack: Optional[float] = None
        self._last_error: str = ""
        self._last_task: dict = {}

    def _build_ws_url(self) -> str:
        return f"{self.server_url}/ws/client?token={self.api_key}"

    def set_api_key(self, api_key: str, server_url: Optional[str] = None):
        self.api_key = (api_key or "").strip()
        if server_url:
            self.server_url = server_url.rstrip("/")
        self.ws_url = self._build_ws_url()
        self._device_id = None
        self._last_heartbeat_ack = None
        self._last_error = ""
        logger.info("Client binding updated: server=%s api_key=%s", self.server_url, bool(self.api_key))

    def _first_capability_api_key(self) -> str:
        for value in (self.capability_api_keys or {}).values():
            if value:
                return value
        return ""

    def set_capability_api_key(self, cap_id: str, api_key: str, server_url: Optional[str] = None):
        if cap_id:
            self.capability_api_keys[cap_id] = (api_key or "").strip()
        if not self.api_key and api_key:
            self.api_key = api_key.strip()
        if server_url:
            self.server_url = server_url.rstrip("/")
        self.ws_url = self._build_ws_url()
        self._last_error = ""

    def set_local_configs(self, configs: dict):
        self._configs = configs or {}
        for cap_id, config in self._configs.items():
            plugin = self._plugins.get(cap_id)
            if plugin:
                plugin.update_config(config)

    def set_local_config(self, cap_id: str, config: dict):
        self._configs[cap_id] = config or {}
        plugin = self._plugins.get(cap_id)
        if plugin:
            plugin.update_config(config or {})

    def get_authorized_capabilities(self) -> list:
        cap_ids = set(self.capability_api_keys.keys()) | set(self._configs.keys())
        return [
            {
                "cap_id": cap_id,
                "api_key_bound": bool(self.capability_api_keys.get(cap_id) or self.api_key),
                "configured": bool(self._configs.get(cap_id)),
            }
            for cap_id in sorted(cap_ids)
        ]

    def register_plugin(self, cap_id: str, plugin_class: type, **kwargs):
        plugin = plugin_class(kwargs)
        self.register_plugin_instance(cap_id, plugin)

    def register_plugin_instance(self, cap_id: str, plugin: CapabilityPlugin):
        plugin.cap_id = cap_id
        self._plugins[cap_id] = plugin
        if cap_id in self._configs:
            plugin.update_config(self._configs[cap_id])
        logger.info("Plugin registered: %s (%s)", cap_id, plugin.__class__.__name__)

    async def run(self):
        self._running = True
        logger.info("AgentHub client starting, server=%s", self.server_url)

        while self._running:
            if not self.api_key:
                self._connected = False
                self._last_error = "Waiting for API Key binding"
                await asyncio.sleep(2)
                continue
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    self._connected_at = time.time()
                    self._last_error = ""
                    logger.info("Connected to AgentHub server")

                    welcome = await asyncio.wait_for(ws.recv(), timeout=10)
                    welcome_data = json.loads(welcome)
                    if welcome_data.get("type") != "welcome":
                        logger.error("Unexpected welcome message: %s", welcome_data)
                        await asyncio.sleep(5)
                        continue

                    self._device_id = welcome_data.get("device_id")
                    capabilities = welcome_data.get("capabilities", [])
                    self._apply_capability_configs(capabilities)
                    logger.info("Device ID: %s", self._device_id)
                    logger.info("Active capabilities: %s", [c.get("cap_id") for c in capabilities])

                    await ws.send(json.dumps({
                        "type": "register",
                        "device_id": self._device_id,
                        "client_version": CLIENT_VERSION,
                        "capabilities": [
                            {
                                "cap_id": cap_id,
                                "name": getattr(plugin, "cap_name", cap_id),
                                "version": getattr(plugin, "VERSION", ""),
                                "actions": self._get_plugin_actions(cap_id),
                            }
                            for cap_id, plugin in self._plugins.items()
                        ],
                        "system_info": {
                            "os": platform.system(),
                            "os_version": platform.version(),
                            "hostname": platform.node(),
                            "python": platform.python_version(),
                        },
                    }, ensure_ascii=False))

                    await asyncio.gather(
                        self._heartbeat_loop(ws),
                        self._message_loop(ws),
                    )

            except websockets.ConnectionClosed as exc:
                self._connected = False
                self._last_error = f"Connection closed: {exc.code} {exc.reason}"
                logger.warning("Connection closed: %s %s", exc.code, exc.reason)
            except asyncio.TimeoutError:
                self._connected = False
                self._last_error = "Connection timeout"
                logger.warning("Connection timeout")
            except ConnectionRefusedError:
                self._connected = False
                self._last_error = "Server refused connection"
                logger.error("Server refused connection")
            except Exception as exc:
                self._connected = False
                self._last_error = str(exc)
                logger.error("Connection error: %s", exc)

            if self._running:
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

        logger.info("AgentHub client stopped")

    def stop(self):
        self._running = False
        self._connected = False

    def get_status(self) -> dict:
        return {
            "client_version": CLIENT_VERSION,
            "server_url": self.server_url,
            "api_key_bound": bool(self.api_key),
            "capability_api_keys": {cap_id: bool(key) for cap_id, key in (self.capability_api_keys or {}).items()},
            "device_id": self._device_id,
            "running": self._running,
            "connected": self._connected,
            "connected_at": self._connected_at,
            "last_heartbeat_ack": self._last_heartbeat_ack,
            "last_error": self._last_error,
            "plugins": [
                {
                    "cap_id": cap_id,
                    "name": getattr(plugin, "cap_name", cap_id),
                    "version": getattr(plugin, "VERSION", ""),
                    "actions": self._get_plugin_actions(cap_id),
                    "configured": bool(self._configs.get(cap_id)),
                }
                for cap_id, plugin in self._plugins.items()
            ],
            "configs": [
                {"cap_id": cap_id, "configured": bool(config)}
                for cap_id, config in self._configs.items()
            ],
            "authorized_capabilities": self.get_authorized_capabilities(),
            "last_task": self._last_task,
            "system_info": {
                "os": platform.system(),
                "os_version": platform.version(),
                "hostname": platform.node(),
                "python": platform.python_version(),
            },
        }

    def _apply_capability_configs(self, capabilities: list):
        for cap in capabilities or []:
            cap_id = cap.get("cap_id")
            if not cap_id:
                continue
            config = cap.get("config") or {}
            self._configs[cap_id] = config
            plugin = self._plugins.get(cap_id)
            if plugin:
                plugin.update_config(config)
                logger.info("Plugin config updated: %s configured=%s", cap_id, bool(config))

    async def _heartbeat_loop(self, ws):
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)
            try:
                await ws.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "plugins": list(self._plugins.keys()),
                }, ensure_ascii=False))
            except Exception as exc:
                logger.error("Heartbeat error: %s", exc)
                break

    async def _message_loop(self, ws):
        while self._running:
            try:
                msg = json.loads(await ws.recv())
                msg_type = msg.get("type")

                if msg_type == "heartbeat_ack":
                    self._last_heartbeat_ack = time.time()
                    continue
                if msg_type == "config_update":
                    capabilities = msg.get("capabilities", [])
                    self._apply_capability_configs(capabilities)
                    logger.info("Config update received: %s", [c.get("cap_id") for c in capabilities])
                elif msg_type == "task":
                    asyncio.create_task(self._handle_task(ws, msg))
                elif msg_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                else:
                    logger.warning("Unknown message type: %s", msg_type)

            except websockets.ConnectionClosed:
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received")
            except Exception as exc:
                logger.error("Message loop error: %s", exc)
                break

    async def _handle_task(self, ws, task: dict):
        task_id = task.get("task_id")
        cap_id = task.get("capability_id")
        action = task.get("action")
        params = task.get("params", {})
        timeout = task.get("timeout", 60)

        logger.info("Task received: %s cap=%s action=%s", task_id, cap_id, action)
        started_at = time.time()

        plugin = self._plugins.get(cap_id)
        if not plugin:
            await ws.send(json.dumps({
                "type": "task_result",
                "task_id": task_id,
                "success": False,
                "error": f"No plugin for capability: {cap_id}",
                "data": None,
            }, ensure_ascii=False))
            return

        try:
            result = await asyncio.wait_for(plugin.execute(action, params), timeout=timeout)
            result["type"] = "task_result"
            result["task_id"] = task_id
        except asyncio.TimeoutError:
            result = {
                "type": "task_result",
                "task_id": task_id,
                "success": False,
                "error": f"Task timeout ({timeout}s)",
                "data": None,
            }
        except Exception as exc:
            logger.error("Task execution error: %s - %s", task_id, exc)
            result = {
                "type": "task_result",
                "task_id": task_id,
                "success": False,
                "error": str(exc),
                "data": None,
            }

        await ws.send(json.dumps(result, ensure_ascii=False))
        self._last_task = {
            "task_id": task_id,
            "capability_id": cap_id,
            "action": action,
            "success": bool(result.get("success")),
            "error": result.get("error"),
            "duration_ms": int((time.time() - started_at) * 1000),
            "finished_at": time.time(),
        }
        logger.info("Task completed: %s success=%s", task_id, result.get("success"))

    def _get_plugin_actions(self, cap_id: str) -> list:
        plugin = self._plugins.get(cap_id)
        return list(getattr(plugin, "ACTIONS", []) or [])

    async def execute_local(self, cap_id: str, action: str, params: dict | None = None, timeout: int = 60) -> dict:
        plugin = self._plugins.get(cap_id)
        if not plugin:
            return {"success": False, "error": f"No plugin for capability: {cap_id}", "data": None}
        try:
            return await asyncio.wait_for(plugin.execute(action, params or {}), timeout=timeout)
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Task timeout ({timeout}s)", "data": None}


def run_client(api_key: str, plugins: Dict[str, CapabilityPlugin], server_url: str = "wss://www.agenthub.wang"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    client = AgentHubClient(api_key=api_key, server_url=server_url)
    for cap_id, plugin in plugins.items():
        client.register_plugin_instance(cap_id, plugin)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        client.stop()
