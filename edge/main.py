"""
AgentHub Edge - AI视觉推理盒子
跨平台运行：Windows / Linux / macOS
功能：ONVIF发现 → RTSP取流 → YOLOv8推理 → 事件上报云端
"""
import os
import sys
import json
import time
import base64
import signal
import logging
import platform
import argparse
import threading
from datetime import datetime
from pathlib import Path

import requests
import cv2
import numpy as np

# 跨平台配置目录
if platform.system() == "Windows":
    CONFIG_DIR = Path(os.environ.get("APPDATA", "~")) / "AgentHub" / "Edge"
elif platform.system() == "Darwin":
    CONFIG_DIR = Path.home() / "Library" / "Application Support" / "AgentHub" / "Edge"
else:
    CONFIG_DIR = Path.home() / ".config" / "agenthub" / "edge"

CONFIG_FILE = CONFIG_DIR / "config.json"
SNAPSHOT_DIR = CONFIG_DIR / "snapshots"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG_DIR / "edge.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("agenthub-edge")


class EdgeConfig:
    """配置管理"""
    
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load()
    
    def _load(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"server_url": "", "api_key": "", "device_id": "", "cameras": [], "rules": []}
    
    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    @property
    def server_url(self):
        return self.config.get("server_url", "").rstrip("/")
    
    @property
    def api_key(self):
        return self.config.get("api_key", "")
    
    @property
    def device_id(self):
        return self.config.get("device_id", "")


class ONVIFDiscovery:
    """ONVIF摄像头发现（纯Python实现，无需额外依赖）"""
    
    ONVIF_PORT = 3702
    DISCOVERY_TIMEOUT = 5
    
    DISCOVERY_MSG = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
               xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery"
               xmlns:tns="http://www.onvif.org/ver10/network/wsdl">
  <soap:Header>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:MessageID>urn:uuid:{uuid}</wsa:MessageID>
  </soap:Header>
  <soap:Body>
    <wsd:Probe>
      <wsd:Types>tns:NetworkVideoTransmitter</wsd:Types>
    </wsd:Probe>
  </soap:Body>
</soap:Envelope>'''
    
    def discover(self, network_interface=""):
        """广播ONVIF发现请求，返回发现的摄像头列表"""
        import socket
        import uuid as uuid_mod
        
        results = []
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.DISCOVERY_TIMEOUT)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            msg = self.DISCOVERY_MSG.format(uuid=str(uuid_mod.uuid4()))
            
            # 向广播地址发送
            targets = ["239.255.255.250", "255.255.255.255"]
            for target in targets:
                try:
                    sock.sendto(msg.encode(), (target, self.ONVIF_PORT))
                except Exception:
                    pass
            
            # 接收响应
            start = time.time()
            while time.time() - start < self.DISCOVERY_TIMEOUT:
                try:
                    data, addr = sock.recvfrom(4096)
                    info = self._parse_response(data, addr[0])
                    if info:
                        results.append(info)
                except socket.timeout:
                    break
            sock.close()
        except Exception as e:
            logger.error(f"ONVIF发现失败: {e}")
        
        # 去重
        seen = set()
        unique = []
        for r in results:
            key = r["ip"]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        return unique
    
    def _parse_response(self, data: bytes, ip: str) -> dict:
        """解析ONVIF发现响应"""
        text = data.decode("utf-8", errors="ignore")
        
        # 检查是否是ONVIF设备
        if "NetworkVideoTransmitter" not in text and "onvif" not in text.lower():
            return None
        
        # 提取XAddrs（设备服务地址）
        import re
        xaddrs_match = re.search(r'<[^>]*XAddrs[^>]*>(.*?)</[^>]*:XAddrs>', text, re.DOTALL)
        onvif_url = xaddrs_match.group(1).strip() if xaddrs_match else f"http://{ip}:80/onvif/device_service"
        
        # 提取设备类型信息
        scopes = re.findall(r'onvif://www\.onvif\.org/(\w+)/(\w+)', text)
        manufacturer = "unknown"
        model = "unknown"
        for category, value in scopes:
            if category == "name":
                manufacturer = value
            elif category == "model":
                model = value
        
        return {
            "ip": ip,
            "onvif_url": onvif_url,
            "manufacturer": manufacturer,
            "model": model,
            "rtsp_port": 554
        }


class RTSPReader:
    """RTSP取流（线程安全，自动重连）"""
    
    def __init__(self, rtsp_url: str, camera_id: str, reconnect_interval: int = 10):
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.reconnect_interval = reconnect_interval
        self.cap = None
        self.connected = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
    
    def connect(self) -> bool:
        """连接RTSP流"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            if self.cap.isOpened():
                self.connected = True
                logger.info(f"摄像头 {self.camera_id[:8]} 连接成功: {self.rtsp_url[:30]}...")
                return True
        except Exception as e:
            logger.error(f"摄像头 {self.camera_id[:8]} 连接失败: {e}")
        
        self.connected = False
        return False
    
    def read_frame(self):
        """读取一帧（线程安全）"""
        with self._lock:
            if not self.cap or not self.cap.isOpened():
                return None
            ret, frame = self.cap.read()
            if not ret:
                self.connected = False
                return None
            return frame
    
    def reconnect(self):
        """重连"""
        self.disconnect()
        time.sleep(self.reconnect_interval)
        return self.connect()
    
    def disconnect(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.connected = False
    
    def stop(self):
        self._stop_event.set()
        self.disconnect()


class YOLODetector:
    """YOLOv8检测器（统一接口，支持多种能力）"""
    
    def __init__(self):
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """加载模型"""
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.warning("ultralytics未安装，AI检测不可用。运行: pip install ultralytics")
            return
        
        model_dir = CONFIG_DIR / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 环境巡检 - 垃圾检测模型
        trash_model_path = model_dir / "trash_detect.pt"
        if trash_model_path.exists():
            self.models["env_inspect"] = YOLO(str(trash_model_path))
            logger.info("✅ 垃圾检测模型已加载")
        else:
            # 使用YOLOv8通用模型作为fallback（可检测bottle, cup等垃圾相关类别）
            self.models["env_inspect"] = YOLO("yolov8n.pt")
            logger.info("⚠️ 使用YOLOv8n通用模型（建议下载专用垃圾检测模型）")
        
        # 高空抛物 - 抛物检测模型
        throw_model_path = model_dir / "throw_detect.pt"
        if throw_model_path.exists():
            self.models["throw_detect"] = YOLO(str(throw_model_path))
            logger.info("✅ 高空抛物检测模型已加载")
        
        # 通用目标追踪（用于智能回查）
        self.models["object_tracking"] = YOLO("yolov8n.pt")
        logger.info("✅ 目标追踪模型(yolov8n)已加载")
    
    def detect(self, frame, capability: str, confidence: float = 0.5):
        """
        执行检测
        返回: [{"class": str, "confidence": float, "bbox": [x1,y1,x2,y2]}]
        """
        if capability not in self.models:
            return []
        
        model = self.models[capability]
        
        # 环境巡检 - 过滤垃圾相关类别
        if capability == "env_inspect":
            trash_classes = [39, 41, 47, 49, 63, 64, 65, 66, 67, 73]  # bottle, cup, fork, knife, potted plant, etc
            results = model(frame, conf=confidence, classes=trash_classes, verbose=False)
        # 高空抛物 - 检测运动物体
        elif capability == "throw_detect":
            results = model(frame, conf=confidence, verbose=False)
        # 目标追踪
        else:
            results = model(frame, conf=confidence, verbose=False)
        
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    detections.append({
                        "class": model.names[int(box.cls)],
                        "confidence": float(box.conf),
                        "bbox": box.xyxy[0].tolist()
                    })
        
        return detections


class ObjectTracker:
    """目标追踪器（基于ByteTrack逻辑的轻量实现）"""
    
    def __init__(self):
        self.tracks = {}  # track_id → {class, first_seen, last_seen, last_bbox}
        self.next_id = 1
        self.max_disappeared = 30  # 消失N帧后标记为离开
    
    def update(self, detections: list, frame_idx: int):
        """更新追踪状态，返回事件列表"""
        events = []
        
        # 简单的IoU匹配
        matched_ids = set()
        
        for det in detections:
            best_id = None
            best_iou = 0.3  # IoU阈值
            
            for tid, track in self.tracks.items():
                if tid in matched_ids:
                    continue
                if track["class"] != det["class"]:
                    continue
                iou = self._compute_iou(track["last_bbox"], det["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid
            
            if best_id:
                # 已有追踪目标，更新
                self.tracks[best_id]["last_seen"] = frame_idx
                self.tracks[best_id]["last_bbox"] = det["bbox"]
                matched_ids.add(best_id)
            else:
                # 新目标
                new_id = self.next_id
                self.next_id += 1
                self.tracks[new_id] = {
                    "class": det["class"],
                    "first_seen": frame_idx,
                    "last_seen": frame_idx,
                    "last_bbox": det["bbox"]
                }
                events.append({"type": "object_appeared", "track_id": new_id, "class": det["class"], "frame": frame_idx})
                matched_ids.add(new_id)
        
        # 检查消失的目标
        disappeared = []
        for tid, track in self.tracks.items():
            if tid not in matched_ids and frame_idx - track["last_seen"] > self.max_disappeared:
                events.append({
                    "type": "object_disappeared",
                    "track_id": tid,
                    "class": track["class"],
                    "first_seen": track["first_seen"],
                    "last_seen": track["last_seen"],
                    "duration_frames": frame_idx - track["first_seen"]
                })
                disappeared.append(tid)
        
        for tid in disappeared:
            del self.tracks[tid]
        
        return events
    
    @staticmethod
    def _compute_iou(box1, box2):
        """计算IoU"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        
        return inter / union if union > 0 else 0


class CloudReporter:
    """云端API通信"""
    
    def __init__(self, config: EdgeConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": config.api_key})
    
    def heartbeat(self, status: str, cameras_online: int, fps: float = None, cpu: float = None, mem: float = None):
        """发送心跳"""
        try:
            resp = self.session.post(f"{self.config.server_url}/api/vision/edge/heartbeat", json={
                "device_id": self.config.device_id,
                "status": status,
                "cameras_online": cameras_online,
                "fps": fps,
                "cpu_percent": cpu,
                "mem_percent": mem
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"心跳发送失败: {e}")
            return False
    
    def pull_config(self):
        """拉取最新配置"""
        try:
            resp = self.session.get(f"{self.config.server_url}/api/vision/edge/config", timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"配置拉取失败: {e}")
        return None
    
    def report_event(self, camera_id: str, event_type: str, severity: str, confidence: float,
                     description: str = None, frame: np.ndarray = None, metadata: dict = None):
        """上报事件"""
        snapshot_b64 = None
        if frame is not None:
            # 压缩截图
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            snapshot_b64 = base64.b64encode(buf).hexdigest()[:100]  # 先压缩hash，实际传base64
            snapshot_b64 = base64.b64encode(buf).decode()
            
            # 也保存本地一份
            local_path = SNAPSHOT_DIR / f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(str(local_path), frame)
        
        try:
            resp = self.session.post(f"{self.config.server_url}/api/vision/edge/events", json={
                "device_id": self.config.device_id,
                "camera_id": camera_id,
                "event_type": event_type,
                "severity": severity,
                "confidence": confidence,
                "description": description,
                "snapshot_base64": snapshot_b64,
                "metadata": metadata
            }, timeout=30)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"事件上报失败: {e}")
            return False


class CameraWorker(threading.Thread):
    """单摄像头工作线程"""
    
    def __init__(self, camera_config: dict, detector: YOLODetector, reporter: CloudReporter, rules: list):
        super().__init__(daemon=True)
        self.camera_config = camera_config
        self.detector = detector
        self.reporter = reporter
        self.rules = [r for r in rules if r.get("camera_id") in (None, camera_config["id"])]
        self.running = True
        self.reader = None
        self.tracker = ObjectTracker()
        self.frame_idx = 0
        self.alert_cooldown = {}  # event_type → last_alert_time
        self.alert_cooldown_seconds = 60  # 同类事件60秒内不重复告警
    
    def run(self):
        rtsp_url = self.camera_config.get("rtsp_url") or self._build_rtsp_url()
        if not rtsp_url:
            logger.error(f"摄像头 {self.camera_config['id'][:8]} 无RTSP地址")
            return
        
        self.reader = RTSPReader(rtsp_url, self.camera_config["id"])
        
        while self.running:
            if not self.reader.connected:
                if not self.reader.connect():
                    time.sleep(10)
                    continue
            
            frame = self.reader.read_frame()
            if frame is None:
                logger.warning(f"摄像头 {self.camera_config['id'][:8]} 读帧失败，尝试重连")
                self.reader.reconnect()
                continue
            
            self.frame_idx += 1
            
            # 按规则执行检测
            for rule in self.rules:
                if not rule.get("enabled", True):
                    continue
                
                capability = rule.get("capability")
                params = rule.get("params", {})
                schedule = rule.get("schedule", {})
                confidence = params.get("confidence", 0.5)
                
                # 检查执行间隔
                interval = schedule.get("seconds", 1)
                if self.frame_idx % max(1, int(interval * 10)) != 0:  # 假设10fps
                    continue
                
                # 执行检测
                detections = self.detector.detect(frame, capability, confidence)
                
                if detections:
                    self._handle_detections(frame, capability, detections, rule)
        
        if self.reader:
            self.reader.stop()
    
    def _build_rtsp_url(self):
        """构建RTSP URL"""
        ip = self.camera_config.get("ip")
        user = self.camera_config.get("username")
        pwd = self.camera_config.get("password")
        port = self.camera_config.get("port", 554)
        cam_type = self.camera_config.get("camera_type", "auto")
        
        if not ip:
            return None
        
        if cam_type == "hikvision":
            return f"rtsp://{user}:{pwd}@{ip}:{port}/Streaming/Channels/101"
        elif cam_type == "dahua":
            return f"rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0"
        elif cam_type == "tp_link":
            return f"rtsp://{user}:{pwd}@{ip}:{port}/stream1"
        else:
            return f"rtsp://{user}:{pwd}@{ip}:{port}/stream1"
    
    def _handle_detections(self, frame, capability, detections, rule):
        """处理检测结果"""
        now = time.time()
        
        if capability == "env_inspect":
            # 环境巡检 - 发现垃圾
            desc_parts = [f"{d['class']}({d['confidence']:.0%})" for d in detections]
            desc = f"发现{len(detections)}处垃圾: {', '.join(desc_parts[:5])}"
            severity = "warning" if len(detections) < 3 else "critical"
            
            if self._should_alert("trash_detected", now):
                self.reporter.report_event(
                    camera_id=self.camera_config["id"],
                    event_type="trash_detected",
                    severity=severity,
                    confidence=max(d["confidence"] for d in detections),
                    description=desc,
                    frame=frame,
                    metadata={"count": len(detections), "items": desc_parts}
                )
                self.alert_cooldown["trash_detected"] = now
        
        elif capability == "throw_detect":
            # 高空抛物
            desc = f"检测到抛物运动，{len(detections)}个运动目标"
            if self._should_alert("throw_detected", now):
                self.reporter.report_event(
                    camera_id=self.camera_config["id"],
                    event_type="throw_detected",
                    severity="critical",
                    confidence=max(d["confidence"] for d in detections),
                    description=desc,
                    frame=frame,
                    metadata={"tracks": len(detections)}
                )
                self.alert_cooldown["throw_detected"] = now
        
        elif capability == "object_tracking":
            # 目标追踪 - 检测目标出现/消失
            events = self.tracker.update(detections, self.frame_idx)
            for evt in events:
                if evt["type"] == "object_disappeared":
                    desc = f"目标消失: {evt['class']}（追踪了{evt['duration_frames']}帧）"
                    self.reporter.report_event(
                        camera_id=self.camera_config["id"],
                        event_type="object_disappeared",
                        severity="info",
                        confidence=0.7,
                        description=desc,
                        frame=frame,
                        metadata=evt
                    )
    
    def _should_alert(self, event_type: str, now: float) -> bool:
        """冷却时间检查"""
        last = self.alert_cooldown.get(event_type, 0)
        return now - last > self.alert_cooldown_seconds
    
    def stop(self):
        self.running = False


class AgentHubEdge:
    """边缘推理主程序"""
    
    def __init__(self, config_path: str = None):
        if config_path:
            global CONFIG_FILE
            CONFIG_FILE = Path(config_path)
        self.config = EdgeConfig()
        self.reporter = CloudReporter(self.config)
        self.detector = None
        self.workers = []
        self.running = False
    
    def setup(self, server_url: str, api_key: str):
        """首次配置"""
        self.config.config["server_url"] = server_url
        self.config.config["api_key"] = api_key
        self.config.save()
        logger.info(f"✅ 配置已保存: server={server_url}")
    
    def discover_cameras(self):
        """发现局域网内的摄像头"""
        logger.info("🔍 正在搜索局域网内的ONVIF摄像头...")
        discovery = ONVIFDiscovery()
        cameras = discovery.discover()
        
        if cameras:
            logger.info(f"📡 发现 {len(cameras)} 个摄像头:")
            for i, cam in enumerate(cameras):
                logger.info(f"  [{i+1}] {cam['ip']} - {cam['manufacturer']} {cam['model']}")
        else:
            logger.info("未发现ONVIF摄像头，请检查网络连接或手动添加")
        
        return cameras
    
    def add_camera(self, ip: str, port: int, username: str, password: str, location: str = "", camera_type: str = "auto"):
        """添加摄像头"""
        cam = {
            "id": f"cam_{int(time.time())}_{len(self.config.config.get('cameras', []))}",
            "ip": ip, "port": port, "username": username, "password": password,
            "location": location, "camera_type": camera_type, "status": "offline"
        }
        self.config.config.setdefault("cameras", []).append(cam)
        self.config.save()
        logger.info(f"✅ 摄像头已添加: {ip}")
        return cam
    
    def sync_config(self):
        """从云端拉取最新配置"""
        cloud_config = self.reporter.pull_config()
        if cloud_config:
            self.config.config["cameras"] = cloud_config.get("cameras", [])
            self.config.config["rules"] = cloud_config.get("rules", [])
            self.config.config["notify_channels"] = cloud_config.get("notify_channels", [])
            self.config.save()
            logger.info(f"✅ 配置已同步: {len(cloud_config.get('cameras', []))}个摄像头, {len(cloud_config.get('rules', []))}条规则")
            return True
        return False
    
    def start(self):
        """启动推理服务"""
        if not self.config.server_url or not self.config.api_key:
            logger.error("❌ 请先配置: agenthub-edge setup --server URL --api-key KEY")
            return
        
        logger.info("=" * 50)
        logger.info("  AgentHub Edge - AI视觉推理盒子")
        logger.info(f"  系统: {platform.system()} {platform.release()}")
        logger.info(f"  Python: {platform.python_version()}")
        logger.info(f"  平台: {self.config.server_url}")
        logger.info("=" * 50)
        
        # 同步云端配置
        self.sync_config()
        
        # 初始化检测器
        try:
            self.detector = YOLODetector()
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            return
        
        cameras = self.config.config.get("cameras", [])
        if not cameras:
            logger.warning("⚠️ 无摄像头配置，尝试ONVIF发现...")
            cameras = self.discover_cameras()
            if not cameras:
                logger.error("❌ 无可用摄像头")
                return
        
        rules = self.config.config.get("rules", [])
        
        # 为每个摄像头启动工作线程
        for cam in cameras:
            worker = CameraWorker(cam, self.detector, self.reporter, rules)
            worker.start()
            self.workers.append(worker)
            logger.info(f"📷 摄像头工作线程已启动: {cam.get('ip', 'unknown')}")
        
        self.running = True
        
        # 心跳循环
        try:
            while self.running:
                import psutil
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                online = sum(1 for w in self.workers if w.reader and w.reader.connected)
                fps = 10.0  # TODO: 实际FPS计算
                
                self.reporter.heartbeat("running", online, fps, cpu, mem)
                
                # 每5分钟同步一次配置
                if int(time.time()) % 300 == 0:
                    self.sync_config()
                
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("正在停止...")
        finally:
            self.stop()
    
    def stop(self):
        """停止所有工作线程"""
        self.running = False
        for w in self.workers:
            w.stop()
        self.workers.clear()
        logger.info("✅ 推理服务已停止")


# ============================================================
# CLI 入口
# ============================================================

def interactive_setup(edge: AgentHubEdge):
    """交互式配置向导"""
    print("\n🔧 AgentHub Edge 首次配置向导")
    print("=" * 40)
    
    server = input("平台地址 (如 https://www.agenthub.wang): ").strip()
    api_key = input("API Key (在平台购买能力后获取): ").strip()
    
    edge.setup(server, api_key)
    
    print("\n📷 摄像头配置")
    print("1. 自动发现 (ONVIF)")
    print("2. 手动输入")
    choice = input("选择 (1/2): ").strip()
    
    if choice == "1":
        cameras = edge.discover_cameras()
        if cameras:
            for cam in cameras:
                add = input(f"  添加 {cam['ip']} ({cam['manufacturer']})? (y/n): ").strip().lower()
                if add == "y":
                    user = input("    用户名 (默认admin): ").strip() or "admin"
                    pwd = input("    密码: ").strip()
                    loc = input("    位置说明 (如: 小区北门): ").strip()
                    edge.add_camera(cam["ip"], cam.get("rtsp_port", 554), user, pwd, loc)
    elif choice == "2":
        while True:
            ip = input("摄像头IP (回车结束): ").strip()
            if not ip:
                break
            user = input("用户名 (默认admin): ").strip() or "admin"
            pwd = input("密码: ").strip()
            port = int(input("端口 (默认554): ").strip() or "554")
            loc = input("位置说明: ").strip()
            print("品牌: 1=海康 2=大华 3=TP-Link 4=通用")
            brand = input("选择 (默认4): ").strip() or "4"
            brand_map = {"1": "hikvision", "2": "dahua", "3": "tp_link", "4": "auto"}
            edge.add_camera(ip, port, user, pwd, loc, brand_map.get(brand, "auto"))
    
    print("\n✅ 配置完成！运行 'agenthub-edge start' 启动服务")


def main():
    parser = argparse.ArgumentParser(description="AgentHub Edge - AI视觉推理盒子")
    parser.add_argument("command", nargs="?", default="start", help="命令: setup/start/discover/version")
    parser.add_argument("--server", help="平台地址")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    edge = AgentHubEdge(args.config)
    
    if args.command == "setup":
        if args.server and args.api_key:
            edge.setup(args.server, args.api_key)
        else:
            interactive_setup(edge)
    
    elif args.command == "discover":
        discovery = ONVIFDiscovery()
        cameras = discovery.discover()
        if cameras:
            print(f"\n📡 发现 {len(cameras)} 个摄像头:")
            for cam in cameras:
                print(f"  {cam['ip']} - {cam['manufacturer']} {cam['model']}")
        else:
            print("未发现摄像头")
    
    elif args.command == "start":
        edge.start()
    
    elif args.command == "version":
        print(f"AgentHub Edge v1.0.0")
        print(f"Python {platform.python_version()} / {platform.system()} {platform.release()}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
