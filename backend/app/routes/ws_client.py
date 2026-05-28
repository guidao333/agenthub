"""WebSocket bridge between AgentHub and local customer clients."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from ..config import SECRET_KEY
from ..models import CustomerConfig, SessionLocal

logger = logging.getLogger("agenthub.ws")

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Track connected customer clients and pending task results."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.device_info: Dict[str, dict] = {}
        self.device_customer: Dict[str, int] = {}
        self.pending_tasks: Dict[str, asyncio.Future] = {}
        self.task_device: Dict[str, str] = {}
        self.device_capabilities: Dict[str, list] = {}
        self.device_runtime: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, device_id: str, customer_id: int):
        await websocket.accept()
        async with self._lock:
            old_ws = self.active_connections.get(device_id)
            if old_ws:
                try:
                    await old_ws.close()
                except Exception:
                    pass
            self.active_connections[device_id] = websocket
            self.device_customer[device_id] = customer_id
            self.device_info[device_id] = {
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": time.time(),
                "status": "online",
            }
            self.device_runtime[device_id] = {}
        logger.info("Device connected: %s customer=%s", device_id, customer_id)

    async def disconnect(self, device_id: str):
        async with self._lock:
            self.active_connections.pop(device_id, None)
            self.device_info.pop(device_id, None)
            self.device_customer.pop(device_id, None)
            self.device_capabilities.pop(device_id, None)
            self.device_runtime.pop(device_id, None)

            dead_task_ids = [task_id for task_id, tid_device in self.task_device.items() if tid_device == device_id]
            for task_id in dead_task_ids:
                future = self.pending_tasks.pop(task_id, None)
                self.task_device.pop(task_id, None)
                if future and not future.done():
                    future.set_result({"success": False, "error": "device_disconnected", "data": None})
        logger.info("Device disconnected: %s", device_id)

    async def send_task(self, device_id: str, task: dict) -> dict:
        task_id = task.get("task_id") or str(uuid.uuid4())
        task["task_id"] = task_id
        task["type"] = "task"

        ws = self.active_connections.get(device_id)
        if not ws:
            logger.warning("Task send failed: device %s not connected", device_id)
            return {"success": False, "error": "device_offline", "data": None}

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.pending_tasks[task_id] = future
        self.task_device[task_id] = device_id

        try:
            await ws.send_json(task)
            logger.info("Task sent: %s -> %s action=%s", task_id, device_id, task.get("action"))
            timeout = task.get("timeout", 60)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Task timeout: %s", task_id)
            return {"success": False, "error": "timeout", "data": None}
        except Exception as exc:
            logger.error("Task send error: %s - %s", task_id, exc)
            return {"success": False, "error": str(exc), "data": None}
        finally:
            self.pending_tasks.pop(task_id, None)
            self.task_device.pop(task_id, None)

    async def handle_task_result(self, device_id: str, result: dict):
        task_id = result.get("task_id")
        if not task_id:
            return

        future = self.pending_tasks.get(task_id)
        if future and not future.done():
            future.set_result(result)
            logger.info("Task result received: %s from %s", task_id, device_id)

    def get_device_for_customer(self, customer_id: int) -> Optional[str]:
        for device_id, mapped_customer in self.device_customer.items():
            if mapped_customer == customer_id and device_id in self.active_connections:
                return device_id
        return None

    def get_online_devices(self) -> list:
        return list(self.active_connections.keys())

    def is_online(self, device_id: str) -> bool:
        return device_id in self.active_connections

    def get_devices_for_customer(self, customer_id: int) -> list:
        devices = []
        now = time.time()
        for device_id, mapped_customer in self.device_customer.items():
            if mapped_customer != customer_id or device_id not in self.active_connections:
                continue
            info = self.device_info.get(device_id, {})
            runtime = self.device_runtime.get(device_id, {})
            last_heartbeat = info.get("last_heartbeat")
            devices.append({
                "device_id": device_id,
                "status": info.get("status", "online"),
                "connected_at": info.get("connected_at"),
                "last_heartbeat": last_heartbeat,
                "last_heartbeat_age_seconds": int(now - last_heartbeat) if last_heartbeat else None,
                "capabilities": self.device_capabilities.get(device_id, []),
                "plugin_capabilities": runtime.get("plugin_capabilities", []),
                "system_info": runtime.get("system_info", {}),
                "client_version": runtime.get("client_version", ""),
                "registered_at": runtime.get("registered_at", ""),
            })
        return devices


manager = ConnectionManager()


@router.websocket("/ws/client")
async def ws_client_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Device API key or JWT token"),
):
    device_id = None

    try:
        customer_id = await _authenticate_device(token)
        if not customer_id:
            await websocket.close(code=4001, reason="Authentication failed")
            return

        device_id = _derive_device_id(token)
        await manager.connect(websocket, device_id, customer_id)

        capabilities = await _get_customer_capabilities(customer_id)
        manager.device_capabilities[device_id] = capabilities
        await websocket.send_json({
            "type": "welcome",
            "device_id": device_id,
            "capabilities": capabilities,
            "server_time": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")
            if msg_type == "heartbeat":
                async with manager._lock:
                    if device_id in manager.device_info:
                        manager.device_info[device_id]["last_heartbeat"] = time.time()
                    if device_id in manager.device_runtime:
                        manager.device_runtime[device_id]["last_heartbeat_payload"] = {
                            "timestamp": msg.get("timestamp"),
                            "plugins": msg.get("plugins", []),
                        }
                await websocket.send_json({"type": "heartbeat_ack", "server_time": time.time()})

                latest_caps = await _get_customer_capabilities(customer_id)
                if latest_caps != manager.device_capabilities.get(device_id):
                    manager.device_capabilities[device_id] = latest_caps
                    await websocket.send_json({"type": "config_update", "capabilities": latest_caps})

            elif msg_type == "task_result":
                await manager.handle_task_result(device_id, msg)

            elif msg_type == "event":
                await _handle_client_event(device_id, customer_id, msg)

            elif msg_type == "register":
                async with manager._lock:
                    manager.device_runtime[device_id] = {
                        **manager.device_runtime.get(device_id, {}),
                        "plugin_capabilities": msg.get("capabilities", []),
                        "system_info": msg.get("system_info", {}),
                        "client_version": msg.get("client_version", ""),
                        "registered_at": datetime.now(timezone.utc).isoformat(),
                    }
                logger.info("Device %s registered capabilities: %s", device_id, msg.get("capabilities", []))

            else:
                logger.warning("Unknown message type from %s: %s", device_id, msg_type)

    except WebSocketDisconnect:
        if device_id:
            await manager.disconnect(device_id)
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", device_id, exc)
        if device_id:
            await manager.disconnect(device_id)


@router.get("/ws/status")
def ws_status():
    devices = []
    for device_id in manager.active_connections:
        info = manager.device_info.get(device_id, {})
        devices.append({
            "device_id": device_id,
            "customer_id": manager.device_customer.get(device_id),
            "connected_at": info.get("connected_at"),
            "last_heartbeat": info.get("last_heartbeat"),
            "capabilities": manager.device_capabilities.get(device_id, []),
            "runtime": manager.device_runtime.get(device_id, {}),
        })
    return {
        "online_devices": len(devices),
        "pending_tasks": len(manager.pending_tasks),
        "devices": devices,
    }


async def _authenticate_device(token: str) -> Optional[int]:
    db = SessionLocal()
    try:
        from ..models import Subscription, User

        if token.startswith("ahk_") or token.startswith("ahv_"):
            sub = db.query(Subscription).filter(
                Subscription.api_key == token,
                Subscription.status == "active",
            ).first()
            if sub:
                return sub.customer_id

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user and user.status == "active":
                return user.id
        except (JWTError, Exception):
            pass

        return None
    finally:
        db.close()


def _derive_device_id(token: str) -> str:
    import hashlib

    return "dev_" + hashlib.sha256(token.encode()).hexdigest()[:12]


async def _get_customer_capabilities(customer_id: int) -> list:
    db = SessionLocal()
    try:
        from ..models import Capability, Subscription

        subs = db.query(Subscription).filter(
            Subscription.customer_id == customer_id,
            Subscription.status == "active",
        ).all()

        capabilities = []
        for sub in subs:
            cap = db.query(Capability).filter(Capability.id == sub.capability_id).first()
            if not cap:
                continue

            config_value = {}
            saved_config = db.query(CustomerConfig).filter(
                CustomerConfig.customer_id == customer_id,
                CustomerConfig.config_key == f"cap_config:{cap.cap_id}",
            ).first()
            if saved_config and saved_config.config_value:
                try:
                    config_value = json.loads(saved_config.config_value)
                except (TypeError, json.JSONDecodeError):
                    logger.warning("Invalid capability config: customer=%s cap=%s", customer_id, cap.cap_id)

            capabilities.append({
                "cap_id": cap.cap_id,
                "name": cap.name,
                "category": cap.category,
                "config": config_value,
                "is_configured": bool(config_value),
            })
        return capabilities
    finally:
        db.close()


async def _handle_client_event(device_id: str, customer_id: int, event: dict):
    logger.info(
        "Event from %s customer=%s type=%s description=%s",
        device_id,
        customer_id,
        event.get("event_type"),
        str(event.get("description", ""))[:100],
    )
