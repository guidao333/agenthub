"""Capability configuration APIs for AgentHub.

Each capability owns a JSON-schema-like configuration template. Customers fill
that template after subscribing, and the desktop client receives the values
through the WebSocket capability list.
"""

import json
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text

from ..models import Base, Capability, CustomerConfig, SessionLocal, Subscription, User, engine
from ..routes.auth import get_current_user

logger = logging.getLogger("agenthub.cap_config")

router = APIRouter(prefix="/cap-config", tags=["capability-config"])

DB_PATH = os.environ.get("AGENTHUB_DB", "/opt/agenthub/data/agenthub.db")


NOTIFICATION_CHANNEL_CATALOG = {
    "title": "通知通道",
    "description": "按角色或事件类型选择通知通道。通道接入信息在配置页统一填写。",
    "options": [
        {"value": "wechat", "label": "微信 / 企业微信", "status": "generic"},
        {"value": "feishu", "label": "飞书", "status": "generic"},
        {"value": "email", "label": "邮件", "status": "generic"},
        {"value": "sms", "label": "短信", "status": "generic"},
    ],
}


ISP_ADAPTER_CATALOG = {
    "billing_system": {
        "title": "计费系统",
        "description": "选择客户实际使用的宽带计费系统。当前已训练凌风计费系统，其他系统可先选择待适配。",
        "options": [
            {"value": "lfradius", "label": "凌风 LFRADIUS", "status": "trained"},
            {"value": "generic_rest", "label": "通用 REST API", "status": "generic"},
            {"value": "other_billing", "label": "其他计费系统", "status": "planned"},
        ],
    },
    "olt_system": {
        "title": "OLT 管理系统",
        "description": "选择 OLT 管理平台，用于查询端口、ONU 状态和执行运维动作。",
        "options": [
            {"value": "miaokai_olt", "label": "秒开 OLT 管理系统", "status": "trained"},
            {"value": "generic_olt", "label": "通用 OLT 管理接口", "status": "generic"},
            {"value": "other_olt", "label": "其他 OLT 管理系统", "status": "planned"},
        ],
    },
    "tr069_system": {
        "title": "TR069 / 光猫管理系统",
        "description": "选择 ACS/TR069 光猫管理系统，用于光猫状态查询、远程重启等动作。",
        "options": [
            {"value": "miaokai_tr069", "label": "秒开 TR069 管理系统", "status": "trained"},
            {"value": "generic_tr069", "label": "通用 TR069 / ACS", "status": "generic"},
            {"value": "other_tr069", "label": "其他 TR069 管理系统", "status": "planned"},
        ],
    },
    "iptv_system": {
        "title": "IPTV 系统",
        "description": "选择 IPTV 业务系统，用于电视账号、套餐和故障相关查询。",
        "options": [
            {"value": "zhgx_iptv", "label": "智慧光迅 IPTV", "status": "trained"},
            {"value": "generic_iptv", "label": "通用 IPTV 接口", "status": "generic"},
            {"value": "none", "label": "暂不接入 IPTV", "status": "none"},
            {"value": "other_iptv", "label": "其他 IPTV 系统", "status": "planned"},
        ],
    },
    "notification_channels": NOTIFICATION_CHANNEL_CATALOG,
    "isp_notification_events": {
        "title": "ISP 业务通知范围",
        "description": "默认覆盖 ISP 智能客服的全部业务能力，客户可按现场需要关闭部分通知。",
        "options": [
            {"value": "account_query", "label": "账号查询结果", "status": "generic"},
            {"value": "fault_diagnosis", "label": "宽带故障诊断", "status": "generic"},
            {"value": "online_status", "label": "用户在线状态", "status": "generic"},
            {"value": "onu_status", "label": "光猫 / ONU 状态", "status": "generic"},
            {"value": "renew_result", "label": "续费 / 停复机结果", "status": "generic"},
            {"value": "ticket_created", "label": "工单派发", "status": "generic"},
            {"value": "system_exception", "label": "系统异常 / 执行失败", "status": "generic"},
            {"value": "daily_summary", "label": "业务日报 / 汇总", "status": "generic"},
        ],
    },
}


AI_MONITOR_ADAPTER_CATALOG = {
    "camera_access": {
        "title": "摄像头接入方式",
        "description": "摄像头实时画面优先通过标准协议接入，品牌直连作为特殊现场的补充方式。",
        "options": [
            {"value": "rtsp", "label": "RTSP 实时流", "status": "generic"},
            {"value": "onvif", "label": "ONVIF 自动发现", "status": "generic"},
            {"value": "brand_direct", "label": "品牌直连", "status": "planned"},
        ],
    },
    "nvr_system": {
        "title": "NVR 录像主机",
        "description": "客户现场默认按 NVR 录像主机存储设计。录像查询、回放、下载片段需要按品牌适配。",
        "options": [
            {"value": "dahua", "label": "大华 NVR", "status": "planned"},
            {"value": "hikvision", "label": "海康 NVR", "status": "planned"},
            {"value": "uniview", "label": "宇视 NVR", "status": "planned"},
            {"value": "tplink", "label": "TP-Link NVR", "status": "planned"},
            {"value": "generic_onvif_replay", "label": "通用 ONVIF 回放", "status": "generic"},
            {"value": "other_nvr", "label": "其他 NVR 品牌", "status": "planned"},
        ],
    },
    "ai_capability_types": {
        "title": "AI 能力类型",
        "description": "录像回查是底层能力，AI 找人、物品遗失、车辆检索是在录像回查之上的专项智能分析能力。",
        "options": [
            {"value": "realtime_alert", "label": "实时告警", "status": "generic"},
            {"value": "patrol_score", "label": "巡检评分", "status": "generic"},
            {"value": "recording_search", "label": "录像回查", "status": "planned"},
            {"value": "person_search", "label": "AI 找人", "status": "planned"},
            {"value": "lost_item", "label": "物品遗失分析", "status": "planned"},
            {"value": "vehicle_search", "label": "车辆检索", "status": "planned"},
            {"value": "throw_detection", "label": "高空抛物", "status": "generic"},
            {"value": "intrusion_detection", "label": "区域入侵 / 越界识别", "status": "planned"},
        ],
    },
    "notification_channels": NOTIFICATION_CHANNEL_CATALOG,
}


class CapabilityConfigTemplate(Base):
    """Developer-defined configuration template for one capability."""

    __tablename__ = "capability_config_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cap_id = Column(String(100), unique=True, nullable=False, index=True)
    schema_json = Column(Text, nullable=False)
    ui_schema = Column(Text, default="{}")
    description = Column(Text, default="")
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")


class ConfigValueInput(BaseModel):
    cap_id: str
    config: dict


class ConfigTemplateInput(BaseModel):
    cap_id: str
    template_schema: dict = Field(alias="schema_json")
    ui_schema: dict = {}
    description: str = ""


def init_config_tables():
    Base.metadata.create_all(bind=engine, tables=[CapabilityConfigTemplate.__table__])
    _seed_default_templates()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _template(
    cap_id: str,
    schema: dict,
    ui_schema: dict,
    description: str,
    now: str,
) -> CapabilityConfigTemplate:
    return CapabilityConfigTemplate(
        cap_id=cap_id,
        schema_json=json.dumps(schema, ensure_ascii=False, indent=2),
        ui_schema=json.dumps(ui_schema, ensure_ascii=False),
        description=description,
        created_at=now,
        updated_at=now,
    )


def _seed_default_templates():
    """Upsert templates for the two canonical capability IDs."""

    now = _now()
    templates = [
        _template(
            cap_id="isp-smart-cs",
            schema={
                "type": "object",
                "required": [
                    "billing_system_type",
                    "billing_url",
                    "billing_username",
                    "billing_password",
                ],
                "properties": {
                    "billing_system_type": {
                        "type": "select",
                        "title": "计费系统类型",
                        "options_key": "billing_system",
                        "default": "lfradius",
                    },
                    "billing_url": {
                        "type": "string",
                        "title": "计费系统地址",
                        "description": "客户本地计费系统 API 地址，例如 http://192.168.1.5:8080",
                        "placeholder": "http://192.168.1.5:8080",
                    },
                    "billing_username": {
                        "type": "string",
                        "title": "计费系统账号",
                        "placeholder": "admin",
                    },
                    "billing_password": {
                        "type": "password",
                        "title": "计费系统密码",
                        "secret": True,
                    },
                    "billing_api_type": {
                        "type": "select",
                        "title": "计费系统接口模式",
                        "enum": ["generic_rest", "lfradius"],
                        "enum_labels": ["通用 REST API", "凌风 LFRADIUS"],
                        "default": "lfradius",
                    },
                    "olt_system_type": {
                        "type": "select",
                        "title": "OLT 管理系统",
                        "options_key": "olt_system",
                        "default": "miaokai_olt",
                    },
                    "tr069_system_type": {
                        "type": "select",
                        "title": "TR069 / 光猫管理系统",
                        "options_key": "tr069_system",
                        "default": "miaokai_tr069",
                    },
                    "iptv_system_type": {
                        "type": "select",
                        "title": "IPTV 系统",
                        "options_key": "iptv_system",
                        "default": "zhgx_iptv",
                    },
                    "tr069_url": {
                        "type": "string",
                        "title": "TR069/ACS 地址",
                        "description": "光猫管理系统地址，可选",
                        "placeholder": "http://192.168.1.1:7547",
                    },
                    "tr069_username": {"type": "string", "title": "TR069 账号"},
                    "tr069_password": {
                        "type": "password",
                        "title": "TR069 密码",
                        "secret": True,
                    },
                    "olt_url": {
                        "type": "string",
                        "title": "OLT 管理地址",
                        "description": "秒开 OLT 或其他 OLT 管理系统地址，可选",
                    },
                    "olt_username": {"type": "string", "title": "OLT 账号"},
                    "olt_password": {
                        "type": "password",
                        "title": "OLT 密码",
                        "secret": True,
                    },
                    "ticket_system_url": {
                        "type": "string",
                        "title": "工单系统地址",
                        "description": "派发工单的系统地址，可选",
                    },
                    "ticket_username": {"type": "string", "title": "工单系统账号"},
                    "ticket_password": {
                        "type": "password",
                        "title": "工单系统密码",
                        "secret": True,
                    },
                    "iptv_url": {
                        "type": "string",
                        "title": "IPTV 系统地址",
                        "description": "可选。未接入 IPTV 时可以留空。",
                    },
                    "iptv_username": {"type": "string", "title": "IPTV 系统账号"},
                    "iptv_password": {
                        "type": "password",
                        "title": "IPTV 系统密码",
                        "secret": True,
                    },
                    "wechat_webhook_url": {
                        "type": "password",
                        "title": "微信 / 企业微信 Webhook",
                        "description": "用于发送客服、装维或管理通知。没有接入时可留空。",
                        "secret": True,
                    },
                    "feishu_webhook_url": {
                        "type": "password",
                        "title": "飞书 Webhook",
                        "description": "用于发送飞书群通知。没有接入时可留空。",
                        "secret": True,
                    },
                    "email_smtp_host": {
                        "type": "string",
                        "title": "邮件 SMTP 地址",
                        "placeholder": "smtp.example.com",
                    },
                    "email_smtp_port": {
                        "type": "number",
                        "title": "邮件 SMTP 端口",
                        "default": 465,
                    },
                    "email_username": {"type": "string", "title": "邮件账号"},
                    "email_password": {
                        "type": "password",
                        "title": "邮件密码 / 授权码",
                        "secret": True,
                    },
                    "sms_provider": {
                        "type": "select",
                        "title": "短信服务商",
                        "enum": ["none", "aliyun", "tencent", "custom"],
                        "enum_labels": ["暂不接入", "阿里云短信", "腾讯云短信", "自定义短信接口"],
                        "default": "none",
                    },
                    "sms_api_url": {
                        "type": "string",
                        "title": "短信接口地址",
                        "description": "自定义短信接口或网关地址，可选。",
                    },
                    "sms_api_key": {
                        "type": "password",
                        "title": "短信 API Key",
                        "secret": True,
                    },
                    "isp_notify_channels": {
                        "type": "multiselect",
                        "title": "ISP 业务通知通道",
                        "options_key": "notification_channels",
                        "default": ["feishu", "wechat"],
                    },
                    "isp_notify_contacts": {
                        "type": "textarea",
                        "title": "ISP 业务通知对象",
                        "description": "用于账号查询、故障诊断、在线状态、ONU 状态、续费结果、工单等通知。每行一个联系人。",
                        "placeholder": "值班客服,13800000000,service@example.com",
                    },
                    "isp_notify_events": {
                        "type": "multiselect",
                        "title": "启用通知的业务范围",
                        "options_key": "isp_notification_events",
                        "default": [
                            "account_query",
                            "fault_diagnosis",
                            "online_status",
                            "onu_status",
                            "renew_result",
                            "ticket_created",
                            "system_exception",
                            "daily_summary",
                        ],
                    },
                    "default_renew_months": {
                        "type": "number",
                        "title": "默认续费月数",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 36,
                    },
                },
            },
            ui_schema={
                "groups": [
                    {
                        "title": "计费系统",
                        "fields": [
                            "billing_system_type",
                            "billing_url",
                            "billing_username",
                            "billing_password",
                            "billing_api_type",
                        ],
                    },
                    {
                        "title": "TR069/光猫管理",
                        "fields": ["tr069_system_type", "tr069_url", "tr069_username", "tr069_password"],
                    },
                    {
                        "title": "OLT 管理",
                        "fields": ["olt_system_type", "olt_url", "olt_username", "olt_password"],
                    },
                    {
                        "title": "IPTV 系统",
                        "fields": ["iptv_system_type", "iptv_url", "iptv_username", "iptv_password"],
                    },
                    {
                        "title": "通知通道接入",
                        "fields": [
                            "wechat_webhook_url",
                            "feishu_webhook_url",
                            "email_smtp_host",
                            "email_smtp_port",
                            "email_username",
                            "email_password",
                            "sms_provider",
                            "sms_api_url",
                            "sms_api_key",
                        ],
                    },
                    {
                        "title": "ISP 业务通知规则",
                        "fields": ["isp_notify_channels", "isp_notify_contacts", "isp_notify_events"],
                    },
                    {
                        "title": "工单系统",
                        "fields": ["ticket_system_url", "ticket_username", "ticket_password"],
                    },
                    {"title": "默认参数", "fields": ["default_renew_months"]},
                ],
            },
            description="ISP 智能客服按系统类型选择适配器，再配置客户本地系统连接信息。通知通道默认覆盖账号查询、故障诊断、在线状态、光猫/ONU 状态、续费结果和工单等全部业务能力，不按固定角色拆分。当前已训练凌风计费、秒开 OLT、秒开 TR069 和智慧光迅 IPTV，后续可继续增加常用系统适配器。",
            now=now,
        ),
        _template(
            cap_id="ai-smart-monitor",
            schema={
                "type": "object",
                "required": ["camera_access_type", "nvr_system_type", "camera_username", "camera_password"],
                "properties": {
                    "camera_access_type": {
                        "type": "select",
                        "title": "摄像头接入方式",
                        "options_key": "camera_access",
                        "default": "onvif",
                    },
                    "nvr_system_type": {
                        "type": "select",
                        "title": "NVR 录像主机品牌",
                        "options_key": "nvr_system",
                        "default": "dahua",
                    },
                    "nvr_host": {
                        "type": "string",
                        "title": "NVR 地址",
                        "description": "NVR 录像主机内网地址，例如 192.168.1.200",
                        "placeholder": "192.168.1.200",
                    },
                    "nvr_port": {
                        "type": "number",
                        "title": "NVR 服务端口",
                        "description": "按品牌接口填写，常见为 80、8000、37777 或 554。",
                        "default": 80,
                    },
                    "nvr_username": {
                        "type": "string",
                        "title": "NVR 账号",
                        "default": "admin",
                    },
                    "nvr_password": {
                        "type": "password",
                        "title": "NVR 密码",
                        "secret": True,
                    },
                    "enabled_ai_capabilities": {
                        "type": "multiselect",
                        "title": "启用 AI 能力类型",
                        "options_key": "ai_capability_types",
                        "default": ["realtime_alert", "patrol_score", "throw_detection"],
                    },
                    "wechat_webhook_url": {
                        "type": "password",
                        "title": "微信 / 企业微信 Webhook",
                        "description": "用于发送微信或企业微信群通知。没有接入时可留空。",
                        "secret": True,
                    },
                    "feishu_webhook_url": {
                        "type": "password",
                        "title": "飞书 Webhook",
                        "description": "用于发送飞书群通知。没有接入时可留空。",
                        "secret": True,
                    },
                    "email_smtp_host": {
                        "type": "string",
                        "title": "邮件 SMTP 地址",
                        "placeholder": "smtp.example.com",
                    },
                    "email_smtp_port": {
                        "type": "number",
                        "title": "邮件 SMTP 端口",
                        "default": 465,
                    },
                    "email_username": {
                        "type": "string",
                        "title": "邮件账号",
                    },
                    "email_password": {
                        "type": "password",
                        "title": "邮件密码 / 授权码",
                        "secret": True,
                    },
                    "sms_provider": {
                        "type": "select",
                        "title": "短信服务商",
                        "enum": ["none", "aliyun", "tencent", "custom"],
                        "enum_labels": ["暂不接入", "阿里云短信", "腾讯云短信", "自定义短信接口"],
                        "default": "none",
                    },
                    "sms_api_url": {
                        "type": "string",
                        "title": "短信接口地址",
                        "description": "自定义短信接口或网关地址，可选。",
                    },
                    "sms_api_key": {
                        "type": "password",
                        "title": "短信 API Key",
                        "secret": True,
                    },
                    "hygiene_notify_channels": {
                        "type": "multiselect",
                        "title": "卫生巡检通知通道",
                        "options_key": "notification_channels",
                        "default": ["feishu", "wechat"],
                    },
                    "hygiene_notify_role": {
                        "type": "string",
                        "title": "卫生巡检负责人角色",
                        "default": "清洁主管",
                    },
                    "hygiene_notify_contacts": {
                        "type": "textarea",
                        "title": "卫生巡检通知对象",
                        "description": "每行一个联系人，可填写姓名、手机号、邮箱、微信/飞书 user_id。例如：张三,13800000000,zhangsan@example.com",
                        "placeholder": "清洁主管,13800000000,clean@example.com",
                    },
                    "hygiene_notify_threshold": {
                        "type": "number",
                        "title": "卫生评分低于多少通知",
                        "description": "低于该分数时通知清洁主管。",
                        "default": 80,
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "throw_notify_channels": {
                        "type": "multiselect",
                        "title": "高空抛物通知通道",
                        "options_key": "notification_channels",
                        "default": ["sms", "wechat", "feishu"],
                    },
                    "throw_notify_role": {
                        "type": "string",
                        "title": "高空抛物负责人角色",
                        "default": "保安队长",
                    },
                    "throw_notify_contacts": {
                        "type": "textarea",
                        "title": "高空抛物通知对象",
                        "description": "每行一个联系人。高空抛物属于紧急告警，建议至少填写手机号和一个即时通讯接收人。",
                        "placeholder": "保安队长,13900000000,security@example.com",
                    },
                    "camera_username": {
                        "type": "string",
                        "title": "摄像头账号",
                        "default": "admin",
                    },
                    "camera_password": {
                        "type": "password",
                        "title": "摄像头密码",
                        "secret": True,
                    },
                    "camera_rtsp_port": {
                        "type": "number",
                        "title": "RTSP 端口",
                        "default": 554,
                    },
                    "patrol_times": {
                        "type": "string",
                        "title": "每日巡检时间",
                        "description": "逗号分隔的小时数，例如 8,14 表示每天 8 点和 14 点",
                        "default": "8,14",
                    },
                    "trash_sensitivity": {
                        "type": "number",
                        "title": "垃圾检测灵敏度",
                        "description": "0.0 到 1.0，越高越敏感",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "throw_sensitivity": {
                        "type": "number",
                        "title": "高空抛物灵敏度",
                        "default": 0.6,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "recording_days": {
                        "type": "number",
                        "title": "录像保留天数",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 30,
                    },
                },
            },
            ui_schema={
                "groups": [
                    {
                        "title": "摄像头接入",
                        "fields": ["camera_access_type", "camera_username", "camera_password", "camera_rtsp_port"],
                    },
                    {
                        "title": "NVR 录像主机",
                        "fields": ["nvr_system_type", "nvr_host", "nvr_port", "nvr_username", "nvr_password"],
                    },
                    {
                        "title": "AI 能力类型",
                        "fields": ["enabled_ai_capabilities"],
                    },
                    {
                        "title": "通知通道接入",
                        "fields": [
                            "wechat_webhook_url",
                            "feishu_webhook_url",
                            "email_smtp_host",
                            "email_smtp_port",
                            "email_username",
                            "email_password",
                            "sms_provider",
                            "sms_api_url",
                            "sms_api_key",
                        ],
                    },
                    {
                        "title": "卫生巡检通知规则",
                        "fields": [
                            "hygiene_notify_channels",
                            "hygiene_notify_role",
                            "hygiene_notify_contacts",
                            "hygiene_notify_threshold",
                        ],
                    },
                    {
                        "title": "高空抛物通知规则",
                        "fields": [
                            "throw_notify_channels",
                            "throw_notify_role",
                            "throw_notify_contacts",
                        ],
                    },
                    {"title": "巡检设置", "fields": ["patrol_times", "trash_sensitivity"]},
                    {"title": "高空抛物设置", "fields": ["throw_sensitivity"]},
                ],
            },
            description="AI 智能监控默认以客户现场 NVR 录像主机作为历史视频来源，摄像头通过 RTSP/ONVIF 接入实时画面。不同事件可配置不同负责人和通知通道，例如卫生巡检发给清洁主管，高空抛物发给保安队长。NVR 的录像查询与片段下载需要按品牌逐步适配，AI 找人、物品遗失等能力建立在录像回查能力之上。",
            now=now,
        ),
    ]

    db = SessionLocal()
    try:
        for template in templates:
            existing = db.query(CapabilityConfigTemplate).filter(
                CapabilityConfigTemplate.cap_id == template.cap_id
            ).first()
            if existing:
                existing.schema_json = template.schema_json
                existing.ui_schema = template.ui_schema
                existing.description = template.description
                existing.updated_at = now
            else:
                db.add(template)
        db.commit()
        logger.info("Default capability config templates are ready")
    except Exception as exc:
        db.rollback()
        logger.error("Seed templates error: %s", exc)
    finally:
        db.close()


def _load_json(value: str, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def _mask_config(config: dict) -> dict:
    masked = dict(config or {})
    for key in list(masked.keys()):
        lowered = key.lower()
        if "password" in lowered or "secret" in lowered or "token" in lowered:
            masked[key] = "******" if masked[key] else ""
    return masked


def _parse_contacts(raw: str) -> dict:
    contacts = [line.strip() for line in str(raw or "").splitlines() if line.strip()]
    text = "\n".join(contacts)
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phones = re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", text)
    return {"raw": contacts, "emails": emails, "phones": phones}


def _is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _is_http_url(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def _test_result(name: str, status: str, message: str) -> dict:
    return {"name": name, "status": status, "message": message}


def _client_status_result(user_id: int) -> dict:
    try:
        from ..routes.ws_client import manager as ws_manager

        device_id = ws_manager.get_device_for_customer(user_id)
        if device_id:
            return _test_result("统一客户端", "ok", f"客户端在线，设备 {device_id} 可接收平台任务。")
        return _test_result("统一客户端", "warn", "未检测到在线客户端。内网系统连通性需要客户端在线后才能测试。")
    except Exception as exc:
        return _test_result("统一客户端", "warn", f"客户端状态暂不可用：{exc}")


async def _run_client_connectivity_test(user_id: int, cap_id: str, config: dict) -> list:
    if cap_id != "isp-smart-cs":
        return []

    try:
        from ..routes.ws_client import manager as ws_manager

        device_id = ws_manager.get_device_for_customer(user_id)
        if not device_id:
            return []

        task_result = await ws_manager.send_task(device_id, {
            "capability_id": cap_id,
            "action": "test_connectivity",
            "params": {"config": config},
            "timeout": 20,
        })
    except Exception as exc:
        return [_test_result("客户端内网连通测试", "error", f"客户端任务下发失败：{exc}")]

    if not task_result.get("success"):
        error = task_result.get("error") or "客户端执行失败"
        return [_test_result("客户端内网连通测试", "error", error)]

    checks = ((task_result.get("data") or {}).get("checks") or [])
    if not checks:
        return [_test_result("客户端内网连通测试", "warn", "客户端未返回具体检测项。")]

    status_map = {"ok": "ok", "skipped": "warn", "error": "error"}
    results = []
    for check in checks:
        name = check.get("name") or "未知系统"
        status = status_map.get(check.get("status"), "warn")
        message = check.get("message") or "未返回检测说明。"
        results.append(_test_result(f"客户端内网测试 - {name}", status, message))
    return results


def _validate_required_fields(template: dict, config: dict) -> list:
    properties = template.get("properties") or {}
    results = []
    for key in template.get("required") or []:
        title = properties.get(key, {}).get("title") or key
        if _is_filled(config.get(key)):
            results.append(_test_result(title, "ok", "已填写。"))
        else:
            results.append(_test_result(title, "error", "必填项未填写。"))
    return results


def _validate_notification_config(config: dict, contacts_key: str = "") -> list:
    results = []
    wechat = config.get("wechat_webhook_url")
    feishu = config.get("feishu_webhook_url")
    email_user = config.get("email_username")
    email_pass = config.get("email_password")
    sms_provider = config.get("sms_provider")
    sms_url = config.get("sms_api_url")

    if wechat:
        results.append(_test_result("微信/企微 Webhook", "ok" if _is_http_url(wechat) else "error", "Webhook 地址格式正常。" if _is_http_url(wechat) else "Webhook 地址应以 http:// 或 https:// 开头。"))
    else:
        results.append(_test_result("微信/企微 Webhook", "warn", "未配置微信/企微通知。"))

    if feishu:
        results.append(_test_result("飞书 Webhook", "ok" if _is_http_url(feishu) else "error", "Webhook 地址格式正常。" if _is_http_url(feishu) else "Webhook 地址应以 http:// 或 https:// 开头。"))
    else:
        results.append(_test_result("飞书 Webhook", "warn", "未配置飞书通知。"))

    if email_user or email_pass:
        results.append(_test_result("邮件通知", "ok" if email_user and email_pass else "error", "邮件账号和授权码已填写。" if email_user and email_pass else "邮件账号和授权码需要同时填写。"))
    else:
        results.append(_test_result("邮件通知", "warn", "未配置邮件通知。"))

    if sms_provider and sms_provider != "none":
        results.append(_test_result("短信通知", "ok" if _is_http_url(sms_url) else "error", "短信接口地址格式正常。" if _is_http_url(sms_url) else "短信接口地址应以 http:// 或 https:// 开头。"))
    else:
        results.append(_test_result("短信通知", "warn", "未配置短信通知。"))

    if contacts_key:
        contacts = _parse_contacts(config.get(contacts_key, ""))
        if contacts["raw"]:
            results.append(_test_result("通知联系人", "ok", f"已识别 {len(contacts['raw'])} 行联系人，手机号 {len(contacts['phones'])} 个，邮箱 {len(contacts['emails'])} 个。"))
        else:
            results.append(_test_result("通知联系人", "warn", "未填写通知联系人。"))
    return results


def _test_isp_config(config: dict) -> list:
    results = []
    billing_url = config.get("billing_url")
    if billing_url:
        results.append(_test_result("计费系统地址", "ok" if _is_http_url(billing_url) else "error", "地址格式正常。" if _is_http_url(billing_url) else "计费系统地址应以 http:// 或 https:// 开头。"))
    for label, key in [
        ("计费系统适配器", "billing_system_type"),
        ("OLT 管理系统适配器", "olt_system_type"),
        ("TR069 光猫管理系统适配器", "tr069_system_type"),
        ("IPTV 系统适配器", "iptv_system_type"),
    ]:
        results.append(_test_result(label, "ok" if _is_filled(config.get(key)) else "warn", f"当前选择：{config.get(key)}" if _is_filled(config.get(key)) else "未选择。"))
    contacts = _parse_contacts(config.get("isp_notify_contacts", ""))
    if contacts["raw"]:
        results.append(_test_result("ISP 业务通知对象", "ok", f"已识别 {len(contacts['raw'])} 行联系人。"))
    else:
        results.append(_test_result("ISP 业务通知对象", "warn", "未填写业务通知对象。"))
    results.extend(_validate_notification_config(config))
    return results


def _test_ai_monitor_config(user_id: int, config: dict) -> list:
    results = []
    results.append(_test_result("摄像头接入方式", "ok" if _is_filled(config.get("camera_access_type")) else "warn", f"当前选择：{config.get('camera_access_type')}" if _is_filled(config.get("camera_access_type")) else "未选择。"))
    results.append(_test_result("NVR 品牌", "ok" if _is_filled(config.get("nvr_system_type")) else "warn", f"当前选择：{config.get('nvr_system_type')}" if _is_filled(config.get("nvr_system_type")) else "未选择。"))
    if _is_filled(config.get("enabled_ai_capabilities")):
        results.append(_test_result("AI 能力类型", "ok", f"已选择 {len(config.get('enabled_ai_capabilities') or [])} 项能力。"))
    else:
        results.append(_test_result("AI 能力类型", "warn", "未选择 AI 能力类型。"))

    for event_key, label in [("hygiene", "卫生巡检"), ("throw", "高空抛物")]:
        contacts = _parse_contacts(config.get(f"{event_key}_notify_contacts", ""))
        channels = config.get(f"{event_key}_notify_channels") or []
        if contacts["raw"] and channels:
            results.append(_test_result(f"{label}通知规则", "ok", f"已配置 {len(channels)} 个通道，{len(contacts['raw'])} 行联系人。"))
        elif contacts["raw"] or channels:
            results.append(_test_result(f"{label}通知规则", "warn", "通知通道和联系人建议同时填写。"))
        else:
            results.append(_test_result(f"{label}通知规则", "warn", "未配置通知规则。"))

    results.extend(_validate_notification_config(config))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        devices = conn.execute(
            "SELECT device_name, status, last_heartbeat FROM vision_devices WHERE user_id=? ORDER BY created_at DESC",
            (str(user_id),),
        ).fetchall()
        if devices:
            online = [d for d in devices if d["status"] == "running" or d["status"] == "online"]
            status = "ok" if online else "warn"
            msg = f"已注册 {len(devices)} 台视觉边缘设备，在线 {len(online)} 台。"
            results.append(_test_result("视觉边缘设备", status, msg))
        else:
            results.append(_test_result("视觉边缘设备", "warn", "还没有注册 AI 监控边缘设备。"))
    finally:
        conn.close()
    results.append(_test_result("NVR/摄像头连通测试", "warn", "RTSP/ONVIF/NVR 真实连通性需要边缘客户端在客户现场网络执行。"))
    return results


def _managed_notify_config(config: dict, event_key: str, channel: str, contacts: dict) -> Optional[dict]:
    base = {
        "managed_by": "ai-smart-monitor",
        "event_key": event_key,
        "role": config.get(f"{event_key}_notify_role", ""),
        "contacts": contacts["raw"],
        "phones": contacts["phones"],
        "emails": contacts["emails"],
    }
    if channel == "wechat":
        webhook = config.get("wechat_webhook_url")
        return {**base, "webhook_url": webhook} if webhook else None
    if channel == "feishu":
        webhook = config.get("feishu_webhook_url")
        return {**base, "webhook_url": webhook} if webhook else None
    if channel == "email":
        if not contacts["emails"] or not config.get("email_password"):
            return None
        return {
            **base,
            "smtp_host": config.get("email_smtp_host"),
            "smtp_port": config.get("email_smtp_port", 465),
            "smtp_user": config.get("email_username"),
            "smtp_pass": config.get("email_password"),
            "to": ",".join(contacts["emails"]),
        }
    if channel == "sms":
        if config.get("sms_provider") == "none" or not contacts["phones"]:
            return None
        return {
            **base,
            "provider": config.get("sms_provider"),
            "api_url": config.get("sms_api_url"),
            "api_key": config.get("sms_api_key"),
            "to": contacts["phones"],
        }
    return None


def _sync_ai_monitor_notifications(user_id: int, config: dict) -> None:
    """Create vision notification channels from the AI monitor capability config."""

    event_rules = [
        {
            "key": "hygiene",
            "channels": config.get("hygiene_notify_channels") or [],
            "contacts": _parse_contacts(config.get("hygiene_notify_contacts", "")),
            "event_types": ["trash_detected", "patrol_score", "hygiene_failed"],
        },
        {
            "key": "throw",
            "channels": config.get("throw_notify_channels") or [],
            "contacts": _parse_contacts(config.get("throw_notify_contacts", "")),
            "event_types": ["throw_detected"],
        },
    ]
    channel_type_map = {
        "wechat": "wechat_webhook",
        "feishu": "feishu_webhook",
        "email": "email",
        "sms": "sms",
    }

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            DELETE FROM vision_notify_channels
            WHERE user_id=? AND config LIKE '%"managed_by": "ai-smart-monitor"%'
            """,
            (str(user_id),),
        )
        for rule in event_rules:
            for channel in rule["channels"]:
                notify_config = _managed_notify_config(config, rule["key"], channel, rule["contacts"])
                if not notify_config:
                    continue
                conn.execute(
                    """
                    INSERT INTO vision_notify_channels
                    (id, user_id, channel_type, config, enabled, event_types)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()),
                        str(user_id),
                        channel_type_map[channel],
                        json.dumps(notify_config, ensure_ascii=False),
                        1,
                        json.dumps(rule["event_types"], ensure_ascii=False),
                    ),
                )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.warning("Sync AI monitor notifications failed: %s", exc)
    finally:
        conn.close()


def _subscription_for(db, user_id: int, cap_id: str):
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "能力不存在")

    sub = db.query(Subscription).filter(
        Subscription.customer_id == user_id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise HTTPException(403, "未订阅该能力")
    return cap, sub


@router.get("/templates/{cap_id}")
def get_config_template(cap_id: str):
    db = SessionLocal()
    try:
        tpl = db.query(CapabilityConfigTemplate).filter(
            CapabilityConfigTemplate.cap_id == cap_id
        ).first()
        if not tpl:
            raise HTTPException(404, "配置模板不存在")
        return {
            "cap_id": tpl.cap_id,
            "schema": _load_json(tpl.schema_json, {}),
            "ui_schema": _load_json(tpl.ui_schema, {}),
            "description": tpl.description,
        }
    finally:
        db.close()


@router.get("/adapter-options/{cap_id}")
def get_adapter_options(cap_id: str):
    if cap_id == "ai-smart-monitor":
        return {
            "cap_id": cap_id,
            "categories": AI_MONITOR_ADAPTER_CATALOG,
        }
    if cap_id != "isp-smart-cs":
        return {"cap_id": cap_id, "categories": {}}
    return {
        "cap_id": cap_id,
        "categories": ISP_ADAPTER_CATALOG,
    }


@router.get("/my-configs")
def get_my_configs(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        configs = db.query(CustomerConfig).filter(
            CustomerConfig.customer_id == current_user.id
        ).all()
        result = {}
        for config in configs:
            value = _load_json(config.config_value, {})
            if isinstance(value, dict):
                value = _mask_config(value)
            result[config.config_key] = value
        return {"configs": result}
    finally:
        db.close()


@router.get("/my-config/{cap_id}")
def get_my_config_for_cap(
    cap_id: str,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        cap, sub = _subscription_for(db, current_user.id, cap_id)
        tpl = db.query(CapabilityConfigTemplate).filter(
            CapabilityConfigTemplate.cap_id == cap_id
        ).first()
        saved = db.query(CustomerConfig).filter(
            CustomerConfig.customer_id == current_user.id,
            CustomerConfig.config_key == f"cap_config:{cap_id}",
        ).first()

        values = _load_json(saved.config_value, {}) if saved else {}
        return {
            "cap_id": cap_id,
            "cap_name": cap.name,
            "template": _load_json(tpl.schema_json, {}) if tpl else None,
            "ui_schema": _load_json(tpl.ui_schema, {}) if tpl else None,
            "description": tpl.description if tpl else "",
            "values": values,
            "is_configured": bool(values),
            "api_key": sub.api_key,
            "subscription_id": sub.id,
        }
    finally:
        db.close()


@router.post("/save")
def save_config(
    input_data: ConfigValueInput,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        cap_id = input_data.cap_id
        config = input_data.config or {}
        _subscription_for(db, current_user.id, cap_id)

        config_key = f"cap_config:{cap_id}"
        now = _now()
        existing = db.query(CustomerConfig).filter(
            CustomerConfig.customer_id == current_user.id,
            CustomerConfig.config_key == config_key,
        ).first()

        if existing:
            existing.config_value = json.dumps(config, ensure_ascii=False)
            existing.updated_at = now
        else:
            db.add(CustomerConfig(
                customer_id=current_user.id,
                config_key=config_key,
                config_value=json.dumps(config, ensure_ascii=False),
                encrypted=1,
                created_at=now,
                updated_at=now,
            ))

        db.commit()
        if cap_id == "ai-smart-monitor":
            _sync_ai_monitor_notifications(current_user.id, config)
        logger.info("Config saved: customer=%s cap=%s", current_user.id, cap_id)
        return {"success": True, "message": "配置已保存，客户端将在下次心跳时自动更新。"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Save config error: %s", exc)
        raise HTTPException(500, "保存配置失败")
    finally:
        db.close()


@router.post("/test")
async def test_config(
    input_data: ConfigValueInput,
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        cap_id = input_data.cap_id
        config = input_data.config or {}
        _subscription_for(db, current_user.id, cap_id)
        tpl = db.query(CapabilityConfigTemplate).filter(
            CapabilityConfigTemplate.cap_id == cap_id
        ).first()
        template = _load_json(tpl.schema_json, {}) if tpl else {}

        results = []
        results.extend(_validate_required_fields(template, config))
        results.append(_client_status_result(current_user.id))

        if cap_id == "isp-smart-cs":
            results.extend(_test_isp_config(config))
            results.extend(await _run_client_connectivity_test(current_user.id, cap_id, config))
        elif cap_id == "ai-smart-monitor":
            results.extend(_test_ai_monitor_config(current_user.id, config))
        else:
            results.append(_test_result("配置结构", "ok", "已完成基础配置字段校验。"))

        status_order = {"error": 3, "warn": 2, "ok": 1}
        worst = max((status_order.get(item["status"], 1) for item in results), default=1)
        overall = "error" if worst == 3 else "warn" if worst == 2 else "ok"
        return {
            "success": overall != "error",
            "status": overall,
            "results": results,
            "message": "检测完成。云端已校验配置格式；内网系统真实连通性需要统一客户端在线后执行。",
        }
    finally:
        db.close()


@router.post("/templates")
def create_template(
    input_data: ConfigTemplateInput,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "developer"):
        raise HTTPException(403, "权限不足")

    db = SessionLocal()
    try:
        now = _now()
        existing = db.query(CapabilityConfigTemplate).filter(
            CapabilityConfigTemplate.cap_id == input_data.cap_id
        ).first()

        if existing:
            existing.schema_json = json.dumps(input_data.template_schema, ensure_ascii=False)
            existing.ui_schema = json.dumps(input_data.ui_schema, ensure_ascii=False)
            existing.description = input_data.description
            existing.updated_at = now
        else:
            db.add(CapabilityConfigTemplate(
                cap_id=input_data.cap_id,
                schema_json=json.dumps(input_data.template_schema, ensure_ascii=False),
                ui_schema=json.dumps(input_data.ui_schema, ensure_ascii=False),
                description=input_data.description,
                created_at=now,
                updated_at=now,
            ))

        db.commit()
        return {"success": True}
    finally:
        db.close()


def get_customer_config_value(customer_id: int, cap_id: str) -> dict:
    """Return the plain config for internal server-side use."""

    db = SessionLocal()
    try:
        saved = db.query(CustomerConfig).filter(
            CustomerConfig.customer_id == customer_id,
            CustomerConfig.config_key == f"cap_config:{cap_id}",
        ).first()
        return _load_json(saved.config_value, {}) if saved else {}
    except Exception:
        return {}
    finally:
        db.close()


# Client-side schema bootstrap. The desktop client uses a capability API Key to pull
# the platform-owned form schema, then stores actual customer private values locally.
CLIENT_TEMPLATE_OVERRIDES = {
    "isp-smart-cs": {
        "description": "连接客户本地计费、TR069、网络设备管理、IPTV、工单和通知系统。",
        "template": FALLBACK_TEMPLATES["isp-smart-cs"]["template"] if "FALLBACK_TEMPLATES" in globals() else {
            "type": "object",
            "required": ["billing_system_type", "billing_url", "billing_username", "billing_password"],
            "properties": {
                "billing_system_type": {"type": "select", "title": "计费系统品牌", "default": "lfradius", "options": [{"value": "lfradius", "label": "凌风 LFRADIUS", "status": "trained"}, {"value": "generic_rest", "label": "通用计费接口", "status": "generic"}, {"value": "other_billing", "label": "其它计费系统", "status": "planned"}]},
                "billing_url": {"type": "string", "title": "计费系统地址", "placeholder": "例如：http://192.168.1.10"},
                "billing_username": {"type": "string", "title": "计费系统账号"},
                "billing_password": {"type": "password", "title": "计费系统密码", "secret": True},
                "billing_api_type": {"type": "select", "title": "接口模式", "default": "lfradius", "options": [{"value": "lfradius", "label": "凌风 LFRADIUS", "status": "trained"}, {"value": "generic_rest", "label": "通用 REST API", "status": "generic"}]},
                "tr069_system_type": {"type": "select", "title": "光猫管理系统品牌", "default": "miaokai_tr069", "options": [{"value": "miaokai_tr069", "label": "秒开 TR069 / ACS", "status": "trained"}, {"value": "generic_tr069", "label": "通用 TR069 / ACS", "status": "generic"}, {"value": "other_tr069", "label": "其它光猫管理系统", "status": "planned"}]},
                "tr069_url": {"type": "string", "title": "光猫管理系统地址"}, "tr069_username": {"type": "string", "title": "光猫管理系统账号"}, "tr069_password": {"type": "password", "title": "光猫管理系统密码", "secret": True},
                "network_mgmt_system_type": {"type": "select", "title": "网络设备管理平台品牌", "default": "miaokai_olt", "options": [{"value": "miaokai_olt", "label": "秒开网络设备管理平台", "status": "trained"}, {"value": "generic_network_mgmt", "label": "通用网络设备管理接口", "status": "generic"}, {"value": "other_network_mgmt", "label": "其它网络设备管理平台", "status": "planned"}]},
                "olt_system_type": {"type": "select", "title": "兼容：OLT管理系统品牌", "default": "miaokai_olt", "options": [{"value": "miaokai_olt", "label": "秒开网络设备管理平台", "status": "trained"}, {"value": "generic_olt", "label": "通用 OLT 接口", "status": "generic"}]},
                "olt_url": {"type": "string", "title": "网络设备管理平台地址", "placeholder": "用于 OLT、PON口、ONU注册等管理"}, "olt_username": {"type": "string", "title": "网络设备管理平台账号"}, "olt_password": {"type": "password", "title": "网络设备管理平台密码", "secret": True},
                "iptv_system_type": {"type": "select", "title": "IPTV系统品牌", "default": "zhgx_iptv", "options": [{"value": "zhgx_iptv", "label": "智慧光迅 IPTV", "status": "trained"}, {"value": "generic_iptv", "label": "通用 IPTV 接口", "status": "generic"}, {"value": "none", "label": "暂不接入 IPTV", "status": "none"}]},
                "iptv_url": {"type": "string", "title": "IPTV系统地址"}, "iptv_username": {"type": "string", "title": "IPTV系统账号"}, "iptv_password": {"type": "password", "title": "IPTV系统密码", "secret": True},
                "ticket_system_url": {"type": "string", "title": "工单系统地址"}, "ticket_username": {"type": "string", "title": "工单系统账号"}, "ticket_password": {"type": "password", "title": "工单系统密码", "secret": True},
                "wechat_webhook_url": {"type": "password", "title": "微信/企业微信 Webhook", "secret": True}, "feishu_webhook_url": {"type": "password", "title": "飞书 Webhook", "secret": True},
                "email_smtp_host": {"type": "string", "title": "邮件 SMTP 地址"}, "email_smtp_port": {"type": "number", "title": "邮件 SMTP 端口", "default": 465}, "email_username": {"type": "string", "title": "邮件账号"}, "email_password": {"type": "password", "title": "邮件密码/授权码", "secret": True},
                "sms_provider": {"type": "select", "title": "短信服务商", "default": "none", "options": [{"value": "none", "label": "暂不接入", "status": "none"}, {"value": "aliyun", "label": "阿里云短信", "status": "generic"}, {"value": "tencent", "label": "腾讯云短信", "status": "generic"}, {"value": "custom", "label": "自定义短信接口", "status": "generic"}]}, "sms_api_url": {"type": "string", "title": "短信接口地址"}, "sms_api_key": {"type": "password", "title": "短信 API Key", "secret": True},
                "isp_notify_channels": {"type": "multiselect", "title": "默认通知通道", "default": ["wechat", "feishu"], "options": [{"value": "wechat", "label": "微信/企业微信", "status": "generic"}, {"value": "feishu", "label": "飞书", "status": "generic"}, {"value": "email", "label": "邮件", "status": "generic"}, {"value": "sms", "label": "短信", "status": "generic"}]},
                "isp_notify_contacts": {"type": "textarea", "title": "默认通知对象", "placeholder": "每行一个：姓名,手机号,邮箱,备注"},
                "isp_notify_events": {"type": "multiselect", "title": "启用通知的业务范围", "default": ["account_query", "fault_diagnosis", "online_status", "onu_status", "renew_result", "ticket_created", "system_exception", "daily_summary"], "options": [{"value": "account_query", "label": "账号查询结果", "status": "generic"}, {"value": "fault_diagnosis", "label": "宽带故障诊断", "status": "generic"}, {"value": "online_status", "label": "用户在线状态", "status": "generic"}, {"value": "onu_status", "label": "光猫/ONU状态", "status": "generic"}, {"value": "renew_result", "label": "续费/停复机结果", "status": "generic"}, {"value": "ticket_created", "label": "工单派发", "status": "generic"}, {"value": "system_exception", "label": "系统异常", "status": "generic"}, {"value": "daily_summary", "label": "业务日报", "status": "generic"}]},
                "default_renew_months": {"type": "number", "title": "默认续费月数", "default": 1, "minimum": 1, "maximum": 36}
            }
        },
        "ui_schema": {"groups": [
            {"title": "计费系统", "description": "宽带账号、套餐、余额、到期、在线状态等业务数据来源。", "fields": ["billing_system_type", "billing_url", "billing_username", "billing_password", "billing_api_type"]},
            {"title": "TR069 / 光猫管理系统", "description": "用于光猫在线状态、光功率、WAN、PPPoE、远程重启等能力。", "fields": ["tr069_system_type", "tr069_url", "tr069_username", "tr069_password"]},
            {"title": "网络设备管理平台", "description": "用于 OLT、PON 口、ONU 注册、网络设备状态等管理，不局限于单台 OLT。", "fields": ["network_mgmt_system_type", "olt_system_type", "olt_url", "olt_username", "olt_password"]},
            {"title": "IPTV 系统", "description": "用于 IPTV 账号、套餐、故障查询。", "fields": ["iptv_system_type", "iptv_url", "iptv_username", "iptv_password"]},
            {"title": "工单系统", "description": "用于自动生成、派发、跟踪装维工单。", "fields": ["ticket_system_url", "ticket_username", "ticket_password"]},
            {"title": "通知通道接入", "description": "所有能力默认可使用这些通道。", "fields": ["wechat_webhook_url", "feishu_webhook_url", "email_smtp_host", "email_smtp_port", "email_username", "email_password", "sms_provider", "sms_api_url", "sms_api_key"]},
            {"title": "业务通知规则", "description": "配置哪些业务事件需要通知，以及默认通知给谁。", "fields": ["isp_notify_channels", "isp_notify_contacts", "isp_notify_events", "default_renew_months"]}
        ]}
    }
}


def _subscription_by_api_key(db, api_key: str, cap_id: str | None = None):
    if not api_key:
        raise HTTPException(401, "缺少能力 API Key")
    sub = db.query(Subscription).filter(Subscription.api_key == api_key, Subscription.status == "active").first()
    if not sub:
        raise HTTPException(403, "API Key 无效或订阅未启用")
    cap = db.query(Capability).filter(Capability.id == sub.capability_id).first()
    if not cap:
        raise HTTPException(404, "能力不存在")
    if cap_id and cap.cap_id != cap_id:
        raise HTTPException(403, "API Key 不属于该能力")
    return cap, sub


@router.get("/client-template/{cap_id}")
def get_client_template_by_api_key(cap_id: str, api_key: str):
    db = SessionLocal()
    try:
        cap, sub = _subscription_by_api_key(db, api_key, cap_id)
        override = CLIENT_TEMPLATE_OVERRIDES.get(cap_id)
        if override:
            return {
                "cap_id": cap.cap_id,
                "cap_name": cap.name,
                "description": override.get("description", ""),
                "template": override["template"],
                "ui_schema": override["ui_schema"],
                "subscription_id": sub.id,
            }
        tpl = db.query(CapabilityConfigTemplate).filter(CapabilityConfigTemplate.cap_id == cap_id).first()
        if not tpl:
            raise HTTPException(404, "配置模板不存在")
        return {
            "cap_id": cap.cap_id,
            "cap_name": cap.name,
            "description": tpl.description,
            "template": _load_json(tpl.schema_json, {}),
            "ui_schema": _load_json(tpl.ui_schema, {}),
            "subscription_id": sub.id,
        }
    finally:
        db.close()
