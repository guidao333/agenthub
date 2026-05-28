"""
AgentHub AI视觉能力 - 云端API
负责：设备管理、事件接收、通知推送、规则配置、计费鉴权
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3
import json
import os
import uuid
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/vision", tags=["AI视觉"])

DB_PATH = os.environ.get("AGENTHUB_DB", "/opt/agenthub/data/agenthub.db")

# ============================================================
# 数据模型
# ============================================================

class DeviceRegister(BaseModel):
    device_name: str
    device_type: str = "edge_box"  # edge_box / pc / raspberry_pi
    os_info: Optional[str] = None  # "Windows 10" / "Ubuntu 22.04" / "macOS 14"
    hostname: Optional[str] = None
    cameras: Optional[List[dict]] = []  # [{ip, port, username, password, location}]

class CameraAdd(BaseModel):
    device_id: str
    ip: str
    port: int = 554
    username: str
    password: str
    location: Optional[str] = None
    camera_type: Optional[str] = None  # auto / hikvision / dahua / tp_link / onvif
    capabilities: Optional[List[str]] = []  # ["env_inspect", "object_tracking", "throw_detect"]

class EventReport(BaseModel):
    device_id: str
    camera_id: str
    event_type: str  # trash_detected / object_lost / throw_detected / person_fall / custom
    severity: str = "info"  # info / warning / critical
    confidence: float = 0.0
    description: Optional[str] = None
    snapshot_base64: Optional[str] = None  # 截图base64
    video_clip_base64: Optional[str] = None  # 视频片段base64（mp4）
    metadata: Optional[dict] = None  # 额外数据（如坐标、分类等）

class NotifyChannel(BaseModel):
    channel_type: str  # email / wechat_webhook / dingtalk_webhook / feishu_webhook / sms
    config: dict  # {"to": "xxx@qq.com"} / {"webhook_url": "https://..."}
    enabled: bool = True
    event_types: Optional[List[str]] = []  # 空=所有事件

class DetectionRule(BaseModel):
    rule_name: str
    camera_id: Optional[str] = None  # 空=所有摄像头
    capability: str  # env_inspect / object_tracking / throw_detect
    enabled: bool = True
    schedule: Optional[dict] = None  # {"type": "interval", "seconds": 300} 或 {"type": "cron", "expr": "0 */5 * * *"}
    params: Optional[dict] = None  # 检测参数（如置信度阈值、检测区域等）
    alert_threshold: Optional[int] = 1  # 连续触发几次才告警

class EdgeHeartbeat(BaseModel):
    device_id: str
    status: str = "running"  # running / idle / error
    cameras_online: int = 0
    fps: Optional[float] = None
    cpu_percent: Optional[float] = None
    mem_percent: Optional[float] = None
    error_msg: Optional[str] = None


# ============================================================
# DB 初始化
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def _user_id(user: User) -> str:
    return str(user.id)

def _user_where(user: User, column: str = "user_id"):
    if user.role == "admin":
        return "", []
    return f" WHERE {column}=?", [_user_id(user)]

def _append_user_condition(user: User, conditions: list, params: list, column: str = "user_id"):
    if user.role != "admin":
        conditions.append(f"{column}=?")
        params.append(_user_id(user))

def _require_device_owner(conn, device_id: str, user: User):
    conditions = ["id=?"]
    params = [device_id]
    _append_user_condition(user, conditions, params)
    row = conn.execute(
        f"SELECT id, user_id FROM vision_devices WHERE {' AND '.join(conditions)}",
        params,
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return row

def _require_camera_owner(conn, camera_id: str, user: User):
    conditions = ["c.id=?"]
    params = [camera_id]
    _append_user_condition(user, conditions, params, "d.user_id")
    row = conn.execute(
        f"""
        SELECT c.* FROM vision_cameras c
        JOIN vision_devices d ON c.device_id = d.id
        WHERE {' AND '.join(conditions)}
        """,
        params,
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Camera not found")
    return row

def init_vision_tables():
    """初始化AI视觉相关表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vision_devices (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_type TEXT DEFAULT 'edge_box',
            os_info TEXT,
            hostname TEXT,
            api_key TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'offline',
            last_heartbeat TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS vision_cameras (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER DEFAULT 554,
            username TEXT,
            password TEXT,
            location TEXT,
            camera_type TEXT DEFAULT 'auto',
            rtsp_url TEXT,
            onvif_url TEXT,
            status TEXT DEFAULT 'offline',
            last_event_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (device_id) REFERENCES vision_devices(id)
        );

        CREATE TABLE IF NOT EXISTS vision_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            camera_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            confidence REAL DEFAULT 0.0,
            description TEXT,
            snapshot_path TEXT,
            video_clip_path TEXT,
            metadata TEXT,
            acknowledged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (device_id) REFERENCES vision_devices(id),
            FOREIGN KEY (camera_id) REFERENCES vision_cameras(id)
        );

        CREATE TABLE IF NOT EXISTS vision_notify_channels (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            config TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            event_types TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vision_rules (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            camera_id TEXT,
            capability TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            schedule TEXT,
            params TEXT,
            alert_threshold INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vision_capability_subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            capability_id TEXT NOT NULL,
            device_id TEXT,
            status TEXT DEFAULT 'active',
            started_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            FOREIGN KEY (capability_id) REFERENCES capabilities(id)
        );
    """)
    conn.commit()
    conn.close()


# ============================================================
# 鉴权
# ============================================================

def verify_api_key(x_api_key: str = Header(...)):
    """边缘端API Key鉴权"""
    conn = get_db()
    row = conn.execute("SELECT id, user_id, device_name, status FROM vision_devices WHERE api_key=?", (x_api_key,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if row["status"] == "disabled":
        raise HTTPException(status_code=403, detail="Device disabled")
    return dict(row)

def verify_subscription(device_info: dict, capability: str):
    """检查是否订阅了该能力"""
    conn = get_db()
    cap_map = {
        "env_inspect": "AI环境巡检",
        "object_tracking": "AI智能回查",
        "throw_detect": "AI高空抛物"
    }
    cap_name = cap_map.get(capability, capability)
    row = conn.execute("""
        SELECT vs.status, vs.expires_at FROM vision_capability_subscriptions vs
        JOIN capabilities c ON vs.capability_id = c.id
        WHERE vs.user_id=? AND c.name LIKE ? AND vs.status='active'
    """, (device_info["user_id"], f"%{cap_name}%")).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=403, detail=f"未订阅能力: {cap_name}")
    if row["expires_at"] and row["expires_at"] < datetime.utcnow().isoformat():
        raise HTTPException(status_code=403, detail="能力已过期，请续费")
    return True


# ============================================================
# 设备管理 API
# ============================================================

@router.post("/devices")
async def register_device(data: DeviceRegister, current_user: User = Depends(get_current_user)):
    """注册边缘设备（用户购买能力后调用）"""
    import secrets
    conn = get_db()
    device_id = str(uuid.uuid4())
    api_key = f"ahv_{secrets.token_hex(24)}"
    
    # TODO: 从登录token获取user_id，暂时用占位
    user_id = _user_id(current_user)
    
    conn.execute(
        "INSERT INTO vision_devices (id, user_id, device_name, device_type, os_info, hostname, api_key) VALUES (?,?,?,?,?,?,?)",
        (device_id, user_id, data.device_name, data.device_type, data.os_info, data.hostname, api_key)
    )
    
    # 如果带了摄像头信息，一并注册
    for cam in data.cameras:
        cam_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO vision_cameras (id, device_id, ip, port, username, password, location, camera_type) VALUES (?,?,?,?,?,?,?,?)",
            (cam_id, device_id, cam.get("ip"), cam.get("port", 554), cam.get("username"), cam.get("password"), cam.get("location"), cam.get("type", "auto"))
        )
    
    conn.commit()
    conn.close()
    return {"device_id": device_id, "api_key": api_key, "message": "设备注册成功，请妥善保管API Key"}


@router.get("/devices")
async def list_devices(current_user: User = Depends(get_current_user)):
    """列出用户的所有设备"""
    conn = get_db()
    where, params = _user_where(current_user)
    devices = conn.execute(
        f"SELECT * FROM vision_devices{where} ORDER BY created_at DESC",
        params,
    ).fetchall()
    result = []
    for d in devices:
        cams = conn.execute("SELECT id, ip, location, status FROM vision_cameras WHERE device_id=?", (d["id"],)).fetchall()
        result.append({**dict(d), "cameras": [dict(c) for c in cams]})
    conn.close()
    return {"devices": result}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, current_user: User = Depends(get_current_user)):
    """删除设备及其关联的摄像头和事件"""
    conn = get_db()
    _require_device_owner(conn, device_id, current_user)
    conn.execute("DELETE FROM vision_events WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM vision_cameras WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM vision_devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()
    return {"message": "设备已删除"}


# ============================================================
# 摄像头管理 API
# ============================================================

@router.post("/cameras")
async def add_camera(data: CameraAdd, current_user: User = Depends(get_current_user)):
    """添加摄像头"""
    conn = get_db()
    _require_device_owner(conn, data.device_id, current_user)
    cam_id = str(uuid.uuid4())
    
    # 自动生成RTSP URL
    rtsp_url = None
    if data.camera_type == "auto" or not data.camera_type:
        # 默认尝试ONVIF通用格式
        rtsp_url = f"rtsp://{data.username}:{data.password}@{data.ip}:{data.port}/stream1"
    elif data.camera_type == "hikvision":
        rtsp_url = f"rtsp://{data.username}:{data.password}@{data.ip}:{data.port}/Streaming/Channels/101"
    elif data.camera_type == "dahua":
        rtsp_url = f"rtsp://{data.username}:{data.password}@{data.ip}:{data.port}/cam/realmonitor?channel=1&subtype=0"
    elif data.camera_type == "tp_link":
        rtsp_url = f"rtsp://{data.username}:{data.password}@{data.ip}:{data.port}/stream1"
    
    conn.execute(
        "INSERT INTO vision_cameras (id, device_id, ip, port, username, password, location, camera_type, rtsp_url) VALUES (?,?,?,?,?,?,?,?,?)",
        (cam_id, data.device_id, data.ip, data.port, data.username, data.password, data.location, data.camera_type, rtsp_url)
    )
    conn.commit()
    conn.close()
    return {"camera_id": cam_id, "rtsp_url": rtsp_url}


@router.get("/cameras")
async def list_cameras(device_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """列出摄像头"""
    conn = get_db()
    conditions = []
    params = []
    if device_id:
        conditions.append("c.device_id=?")
        params.append(device_id)
    _append_user_condition(current_user, conditions, params, "d.user_id")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(
        f"""
        SELECT c.* FROM vision_cameras c
        JOIN vision_devices d ON c.device_id = d.id
        {where}
        ORDER BY c.created_at DESC
        """,
        params,
    ).fetchall()
    conn.close()
    return {"cameras": [dict(r) for r in rows]}


@router.post("/cameras/{camera_id}/discover")
async def discover_camera(camera_id: str, current_user: User = Depends(get_current_user)):
    """ONVIF自动发现摄像头能力"""
    conn = get_db()
    cam = _require_camera_owner(conn, camera_id, current_user)
    if not cam:
        conn.close()
        raise HTTPException(status_code=404, detail="摄像头不存在")
    
    # TODO: 实际调用ONVIF发现逻辑，返回设备信息
    # 这里先返回模拟数据，边缘端会实际执行
    conn.close()
    return {
        "camera_id": camera_id,
        "message": "ONVIF发现任务已下发到边缘端",
        "supported_features": ["RTSP", "ONVIF", "PTZ", "motion_detection"]
    }


# ============================================================
# 边缘端 API（推理盒子调用）
# ============================================================

@router.post("/edge/heartbeat")
async def edge_heartbeat(data: EdgeHeartbeat, device: dict = Depends(verify_api_key)):
    """边缘端心跳上报"""
    conn = get_db()
    conn.execute(
        "UPDATE vision_devices SET status=?, last_heartbeat=datetime('now') WHERE id=?",
        (data.status, device["id"])
    )
    # 更新关联摄像头在线状态
    limit = int(data.cameras_online)
    conn.execute(
        "UPDATE vision_cameras SET status='online' WHERE device_id=? LIMIT " + str(limit),
        (device["id"],)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "server_time": datetime.utcnow().isoformat()}


@router.get("/edge/config")
async def edge_get_config(device: dict = Depends(verify_api_key)):
    """边缘端拉取完整配置（摄像头列表、检测规则、通知配置）"""
    conn = get_db()
    
    # 获取摄像头
    cameras = conn.execute("SELECT * FROM vision_cameras WHERE device_id=?", (device["id"],)).fetchall()
    
    # 获取检测规则
    rules = conn.execute("SELECT * FROM vision_rules WHERE user_id=? AND enabled=1", (device["user_id"],)).fetchall()
    
    # 获取通知渠道（边缘端可能不需要，但可以返回用于测试）
    notify = conn.execute("SELECT * FROM vision_notify_channels WHERE user_id=? AND enabled=1", (device["user_id"],)).fetchall()
    
    conn.close()
    
    return {
        "device_id": device["id"],
        "cameras": [dict(c) for c in cameras],
        "rules": [{**dict(r), "schedule": json.loads(r["schedule"] or "{}"), "params": json.loads(r["params"] or "{}")} for r in rules],
        "notify_channels": [{**dict(n), "config": json.loads(n["config"] or "{}"), "event_types": json.loads(n["event_types"] or "[]")} for n in notify],
        "config_version": datetime.utcnow().isoformat()
    }


@router.post("/edge/events")
async def edge_report_event(data: EventReport, device: dict = Depends(verify_api_key)):
    """边缘端上报检测事件"""
    import base64
    conn = get_db()
    event_id = str(uuid.uuid4())
    snapshot_path = None
    
    # 保存截图
    if data.snapshot_base64:
        snap_dir = "/opt/agenthub/data/snapshots"
        os.makedirs(snap_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{data.event_type}_{data.camera_id[:8]}_{ts}.jpg"
        snapshot_path = f"{snap_dir}/{filename}"
        with open(snapshot_path, "wb") as f:
            f.write(base64.b64decode(data.snapshot_base64))
    
    # Save video clip if present
    video_clip_path = None
    if data.video_clip_base64:
        clip_dir = "/opt/agenthub/data/clips"
        os.makedirs(clip_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        clip_filename = f"{data.event_type}_{data.camera_id[:8]}_{ts}.mp4"
        video_clip_path = f"{clip_dir}/{clip_filename}"
        with open(video_clip_path, "wb") as f:
            f.write(base64.b64decode(data.video_clip_base64))

    camera = conn.execute(
        "SELECT id FROM vision_cameras WHERE id=? AND device_id=?",
        (data.camera_id, device["id"]),
    ).fetchone()
    if not camera:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found for this device")

    conn.execute(
        "INSERT INTO vision_events (id, user_id, device_id, camera_id, event_type, severity, confidence, description, snapshot_path, video_clip_path, metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (event_id, device["user_id"], device["id"], data.camera_id, data.event_type, data.severity, data.confidence, data.description, snapshot_path, video_clip_path, json.dumps(data.metadata or {}))
    )
    conn.commit()
    
    # 触发通知推送（异步）
    await _trigger_notifications(conn, device["user_id"], {
        "event_id": event_id,
        "event_type": data.event_type,
        "severity": data.severity,
        "description": data.description,
        "camera_id": data.camera_id,
        "confidence": data.confidence,
        "snapshot_path": snapshot_path,
        "video_clip_path": video_clip_path
    })
    
    conn.close()
    return {"event_id": event_id, "status": "recorded"}


# ============================================================
# 事件查询 API（管理后台用）
# ============================================================

@router.get("/events")
async def list_events(
    device_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """查询事件列表"""
    conn = get_db()
    conditions = []
    params = []
    
    if device_id:
        conditions.append("device_id=?")
        params.append(device_id)
    if camera_id:
        conditions.append("camera_id=?")
        params.append(camera_id)
    if event_type:
        conditions.append("event_type=?")
        params.append(event_type)
    if severity:
        conditions.append("severity=?")
        params.append(severity)
    if acknowledged is not None:
        conditions.append("acknowledged=?")
        params.append(acknowledged)
    _append_user_condition(current_user, conditions, params)
    
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    total = conn.execute(f"SELECT COUNT(*) FROM vision_events{where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM vision_events{where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    conn.close()
    
    return {
        "total": total,
        "events": [dict(r) for r in rows]
    }


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: str, current_user: User = Depends(get_current_user)):
    """确认事件"""
    conn = get_db()
    conditions = ["id=?"]
    params = [event_id]
    _append_user_condition(current_user, conditions, params)
    conn.execute(
        f"UPDATE vision_events SET acknowledged=1 WHERE {' AND '.join(conditions)}",
        params,
    )
    conn.commit()
    conn.close()
    return {"message": "已确认"}


# ============================================================
# 检测规则 API
# ============================================================

@router.post("/rules")
async def create_rule(data: DetectionRule, current_user: User = Depends(get_current_user)):
    """创建检测规则"""
    conn = get_db()
    if data.camera_id:
        _require_camera_owner(conn, data.camera_id, current_user)
    rule_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO vision_rules (id, user_id, rule_name, camera_id, capability, enabled, schedule, params, alert_threshold) VALUES (?,?,?,?,?,?,?,?,?)",
        (rule_id, _user_id(current_user), data.rule_name, data.camera_id, data.capability, int(data.enabled), json.dumps(data.schedule or {}), json.dumps(data.params or {}), data.alert_threshold)
    )
    conn.commit()
    conn.close()
    return {"rule_id": rule_id}


@router.get("/rules")
async def list_rules(capability: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """列出检测规则"""
    conn = get_db()
    conditions = []
    params = []
    if capability:
        conditions.append("capability=?")
        params.append(capability)
    _append_user_condition(current_user, conditions, params)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(f"SELECT * FROM vision_rules{where} ORDER BY created_at DESC", params).fetchall()
    conn.close()
    return {"rules": [{**dict(r), "schedule": json.loads(r["schedule"] or "{}"), "params": json.loads(r["params"] or "{}")} for r in rows]}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, data: DetectionRule, current_user: User = Depends(get_current_user)):
    """更新检测规则"""
    conn = get_db()
    if data.camera_id:
        _require_camera_owner(conn, data.camera_id, current_user)
    conditions = ["id=?"]
    params = [data.rule_name, data.camera_id, data.capability, int(data.enabled), json.dumps(data.schedule or {}), json.dumps(data.params or {}), data.alert_threshold, rule_id]
    _append_user_condition(current_user, conditions, params)
    conn.execute(
        f"UPDATE vision_rules SET rule_name=?, camera_id=?, capability=?, enabled=?, schedule=?, params=?, alert_threshold=? WHERE {' AND '.join(conditions)}",
        params
    )
    conn.commit()
    conn.close()
    return {"message": "规则已更新"}


# ============================================================
# 通知渠道 API
# ============================================================

@router.post("/notify/channels")
async def add_notify_channel(data: NotifyChannel, current_user: User = Depends(get_current_user)):
    """添加通知渠道"""
    conn = get_db()
    ch_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO vision_notify_channels (id, user_id, channel_type, config, enabled, event_types) VALUES (?,?,?,?,?,?)",
        (ch_id, _user_id(current_user), data.channel_type, json.dumps(data.config), int(data.enabled), json.dumps(data.event_types or []))
    )
    conn.commit()
    conn.close()
    return {"channel_id": ch_id}


@router.get("/notify/channels")
async def list_notify_channels(current_user: User = Depends(get_current_user)):
    """列出通知渠道"""
    conn = get_db()
    where, params = _user_where(current_user)
    rows = conn.execute(
        f"SELECT * FROM vision_notify_channels{where} ORDER BY created_at DESC",
        params,
    ).fetchall()
    conn.close()
    return {"channels": [{**dict(r), "config": json.loads(r["config"] or "{}"), "event_types": json.loads(r["event_types"] or "[]")} for r in rows]}


@router.post("/notify/test/{channel_id}")
async def test_notify_channel(channel_id: str, current_user: User = Depends(get_current_user)):
    """测试通知渠道"""
    conn = get_db()
    conditions = ["id=?"]
    params = [channel_id]
    _append_user_condition(current_user, conditions, params)
    ch = conn.execute(
        f"SELECT * FROM vision_notify_channels WHERE {' AND '.join(conditions)}",
        params,
    ).fetchone()
    conn.close()
    if not ch:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    config = json.loads(ch["config"])
    result = await _send_notification(ch["channel_type"], config, "🔧 AgentHub通知测试", "如果您收到此消息，说明通知渠道配置成功！")
    
    return {"success": result, "message": "测试消息已发送" if result else "发送失败"}


# ============================================================
# 统计 API
# ============================================================

@router.get("/stats")
async def get_stats(device_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """获取统计数据"""
    conn = get_db()
    
    conditions = []
    params = []
    if device_id:
        conditions.append("device_id=?")
        params.append(device_id)
    _append_user_condition(current_user, conditions, params)
    base_cond = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    total_events = conn.execute(f"SELECT COUNT(*) FROM vision_events {base_cond}", params).fetchone()[0]
    today_conditions = ["date(created_at)=date('now')"] + conditions
    unack_conditions = ["acknowledged=0"] + conditions
    today_events = conn.execute(
        f"SELECT COUNT(*) FROM vision_events WHERE {' AND '.join(today_conditions)}",
        params,
    ).fetchone()[0]
    
    by_type = conn.execute(f"SELECT event_type, COUNT(*) as cnt FROM vision_events {base_cond} GROUP BY event_type ORDER BY cnt DESC", params).fetchall()
    by_severity = conn.execute(f"SELECT severity, COUNT(*) as cnt FROM vision_events {base_cond} GROUP BY severity", params).fetchall()
    unacknowledged = conn.execute(
        f"SELECT COUNT(*) FROM vision_events WHERE {' AND '.join(unack_conditions)}",
        params,
    ).fetchone()[0]
    
    conn.close()
    return {
        "total_events": total_events,
        "today_events": today_events,
        "unacknowledged": unacknowledged,
        "by_type": [dict(r) for r in by_type],
        "by_severity": [dict(r) for r in by_severity]
    }


# ============================================================
# 通知推送内部实现
# ============================================================

async def _trigger_notifications(conn, user_id: str, event: dict):
    """触发通知推送"""
    channels = conn.execute("SELECT * FROM vision_notify_channels WHERE user_id=? AND enabled=1", (user_id,)).fetchall()
    
    for ch in channels:
        config = json.loads(ch["config"] or "{}")
        event_types = json.loads(ch["event_types"] or "[]")
        
        # 过滤事件类型
        if event_types and event["event_type"] not in event_types:
            continue
        
        severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(event["severity"], "📢")
        title = f"{severity_emoji} AI视觉告警 - {event['event_type']}"
        body = f"摄像头: {event['camera_id'][:8]}\n置信度: {event['confidence']:.1%}\n描述: {event['description'] or '无'}"
        
        await _send_notification(ch["channel_type"], config, title, body)


async def _send_notification(channel_type: str, config: dict, title: str, body: str) -> bool:
    """实际发送通知"""
    import httpx
    
    try:
        if channel_type == "email":
            return await _send_email(config, title, body)
        elif channel_type == "wechat_webhook":
            # 企业微信群机器人Webhook
            webhook_url = config.get("webhook_url", "")
            if not webhook_url:
                return False
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json={
                    "msgtype": "text",
                    "text": {"content": f"{title}\n{body}"}
                })
                return resp.status_code == 200
        elif channel_type == "dingtalk_webhook":
            # 钉钉群机器人Webhook
            webhook_url = config.get("webhook_url", "")
            secret = config.get("secret", "")  # 加签密钥
            if not webhook_url:
                return False
            url = webhook_url
            if secret:
                import hashlib, hmac, time, urllib.parse
                timestamp = str(round(time.time() * 1000))
                string_to_sign = f"{timestamp}\n{secret}"
                hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={
                    "msgtype": "markdown",
                    "markdown": {"title": title, "text": f"## {title}\n\n{body}"}
                })
                return resp.status_code == 200
        elif channel_type == "feishu_webhook":
            # 飞书群机器人Webhook
            webhook_url = config.get("webhook_url", "")
            if not webhook_url:
                return False
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json={
                    "msg_type": "interactive",
                    "card": {
                        "header": {"title": {"tag": "plain_text", "content": title}},
                        "elements": [{"tag": "markdown", "content": body}]
                    }
                })
                return resp.status_code == 200
        elif channel_type == "sms":
            api_url = config.get("api_url", "")
            api_key = config.get("api_key", "")
            phones = config.get("to") or config.get("phones") or []
            if isinstance(phones, str):
                phones = [phones]
            if not api_url or not phones:
                return False
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(api_url, json={
                    "api_key": api_key,
                    "phones": phones,
                    "title": title,
                    "content": body,
                })
                return 200 <= resp.status_code < 300
    except Exception:
        return False


async def _send_email(config: dict, title: str, body: str) -> bool:
    """发送邮件通知"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_host = config.get("smtp_host", "smtp.qq.com")
    smtp_port = config.get("smtp_port", 465)
    smtp_user = config.get("smtp_user", "5690300@qq.com")
    smtp_pass = config.get("smtp_pass", "")
    to_email = config.get("to", "")
    to_emails = [item.strip() for item in str(to_email).split(",") if item.strip()]
    
    if not smtp_pass or not to_emails:
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = ",".join(to_emails)
        msg["Subject"] = title
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_emails, msg.as_string())
        return True
    except Exception:
        return False


# --- AI Vision Chat API ---

class VisionChatRequest(BaseModel):
    message: str
    session_id: str = ""

class VisionChatResponse(BaseModel):
    type: str
    content: str

_vision_chat_engine = None

def _get_chat_engine():
    global _vision_chat_engine
    if _vision_chat_engine is None:
        from ..services.vision_chat_engine import VisionChatEngine
        _vision_chat_engine = VisionChatEngine()
    return _vision_chat_engine

# Session history store (in-memory, per session_id)
_chat_sessions: list = []

def _get_session_history(session_id: str, limit: int = 20) -> list:
    for s in _chat_sessions:
        if s["id"] == session_id:
            return s["messages"][-limit:]
    return []

def _add_session_message(session_id: str, role: str, content: str):
    for s in _chat_sessions:
        if s["id"] == session_id:
            s["messages"].append({"role": role, "content": content})
            if len(s["messages"]) > 50:
                s["messages"] = s["messages"][-50:]
            return
    _chat_sessions.append({"id": session_id, "messages": [{"role": role, "content": content}]})
    if len(_chat_sessions) > 100:
        _chat_sessions.pop(0)

@router.post("/chat", response_model=VisionChatResponse)
def vision_chat(req: VisionChatRequest):
    import uuid
    session_id = req.session_id or str(uuid.uuid4())[:8]

    history = _get_session_history(session_id)
    _add_session_message(session_id, "user", req.message)

    engine = _get_chat_engine()
    result = engine.chat(
        message=req.message,
        context=history,
        device_id=None,
    )

    _add_session_message(session_id, "assistant", result.get("content", ""))

    return VisionChatResponse(
        type=result.get("type", "reply"),
        content=result.get("content", ""),
    )
