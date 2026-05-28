"""Local browser workbench for the AgentHub desktop client."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger("agenthub.workbench")


CAP_NAMES = {
    "isp-smart-cs": "ISP智能客服",
    "ai-smart-monitor": "AI智能监控",
}


def _field(field_type, title, **kwargs):
    data = {"type": field_type, "title": title}
    data.update(kwargs)
    return data


def _option(value, label, status="generic"):
    return {"value": value, "label": label, "status": status}


FALLBACK_TEMPLATES = {
    "isp-smart-cs": {
        "cap_id": "isp-smart-cs",
        "cap_name": "ISP智能客服",
        "description": "连接客户本地计费、TR069、网络设备管理、IPTV、工单和通知系统。",
        "template": {
            "type": "object",
            "required": ["billing_system_type", "billing_url", "billing_username", "billing_password"],
            "properties": {
                "billing_system_type": _field("select", "计费系统品牌", default="lfradius", options=[
                    _option("lfradius", "凌风 LFRADIUS", "trained"),
                    _option("generic_rest", "通用计费接口"),
                    _option("other_billing", "其它计费系统", "planned"),
                ]),
                "billing_url": _field("string", "计费系统地址", placeholder="例如：http://192.168.1.10"),
                "billing_username": _field("string", "计费系统账号"),
                "billing_password": _field("password", "计费系统密码", secret=True),
                "billing_api_type": _field("select", "接口模式", default="lfradius", options=[
                    _option("lfradius", "凌风 LFRADIUS", "trained"),
                    _option("generic_rest", "通用 REST API"),
                ]),
                "tr069_system_type": _field("select", "光猫管理系统品牌", default="miaokai_tr069", options=[
                    _option("miaokai_tr069", "秒开 TR069 / ACS", "trained"),
                    _option("generic_tr069", "通用 TR069 / ACS"),
                    _option("other_tr069", "其它光猫管理系统", "planned"),
                ]),
                "tr069_url": _field("string", "光猫管理系统地址"),
                "tr069_username": _field("string", "光猫管理系统账号"),
                "tr069_password": _field("password", "光猫管理系统密码", secret=True),
                "network_mgmt_system_type": _field("select", "网络设备管理平台品牌", default="miaokai_olt", options=[
                    _option("miaokai_olt", "秒开网络设备管理平台", "trained"),
                    _option("generic_network_mgmt", "通用网络设备管理接口"),
                    _option("other_network_mgmt", "其它网络设备管理平台", "planned"),
                ]),
                "olt_system_type": _field("select", "兼容：OLT管理系统品牌", default="miaokai_olt", options=[
                    _option("miaokai_olt", "秒开网络设备管理平台", "trained"),
                    _option("generic_olt", "通用 OLT 接口"),
                ]),
                "olt_url": _field("string", "网络设备管理平台地址", placeholder="用于 OLT、PON口、ONU注册等管理"),
                "olt_username": _field("string", "网络设备管理平台账号"),
                "olt_password": _field("password", "网络设备管理平台密码", secret=True),
                "iptv_system_type": _field("select", "IPTV系统品牌", default="zhgx_iptv", options=[
                    _option("zhgx_iptv", "智慧光迅 IPTV", "trained"),
                    _option("generic_iptv", "通用 IPTV 接口"),
                    _option("none", "暂不接入 IPTV", "none"),
                ]),
                "iptv_url": _field("string", "IPTV系统地址"),
                "iptv_username": _field("string", "IPTV系统账号"),
                "iptv_password": _field("password", "IPTV系统密码", secret=True),
                "ticket_system_url": _field("string", "工单系统地址"),
                "ticket_username": _field("string", "工单系统账号"),
                "ticket_password": _field("password", "工单系统密码", secret=True),
                "wechat_webhook_url": _field("password", "微信/企业微信 Webhook", secret=True),
                "feishu_webhook_url": _field("password", "飞书 Webhook", secret=True),
                "email_smtp_host": _field("string", "邮件 SMTP 地址"),
                "email_smtp_port": _field("number", "邮件 SMTP 端口", default=465),
                "email_username": _field("string", "邮件账号"),
                "email_password": _field("password", "邮件密码/授权码", secret=True),
                "sms_provider": _field("select", "短信服务商", default="none", options=[
                    _option("none", "暂不接入", "none"),
                    _option("aliyun", "阿里云短信"),
                    _option("tencent", "腾讯云短信"),
                    _option("custom", "自定义短信接口"),
                ]),
                "sms_api_url": _field("string", "短信接口地址"),
                "sms_api_key": _field("password", "短信 API Key", secret=True),
                "isp_notify_channels": _field("multiselect", "默认通知通道", default=["wechat", "feishu"], options=[
                    _option("wechat", "微信/企业微信"),
                    _option("feishu", "飞书"),
                    _option("email", "邮件"),
                    _option("sms", "短信"),
                ]),
                "isp_notify_contacts": _field("textarea", "默认通知对象", placeholder="每行一个：姓名,手机号,邮箱,备注"),
                "isp_notify_events": _field("multiselect", "启用通知的业务范围", default=[
                    "account_query", "fault_diagnosis", "online_status", "onu_status",
                    "renew_result", "ticket_created", "system_exception", "daily_summary",
                ], options=[
                    _option("account_query", "账号查询结果"),
                    _option("fault_diagnosis", "宽带故障诊断"),
                    _option("online_status", "用户在线状态"),
                    _option("onu_status", "光猫/ONU状态"),
                    _option("renew_result", "续费/停复机结果"),
                    _option("ticket_created", "工单派发"),
                    _option("system_exception", "系统异常"),
                    _option("daily_summary", "业务日报"),
                ]),
                "default_renew_months": _field("number", "默认续费月数", default=1, minimum=1, maximum=36),
            },
        },
        "ui_schema": {"groups": [
            {"title": "计费系统", "description": "宽带账号、套餐、余额、到期、在线状态等业务数据来源。", "fields": ["billing_system_type", "billing_url", "billing_username", "billing_password", "billing_api_type"]},
            {"title": "TR069 / 光猫管理系统", "description": "用于光猫在线状态、光功率、WAN、PPPoE、远程重启等能力。", "fields": ["tr069_system_type", "tr069_url", "tr069_username", "tr069_password"]},
            {"title": "网络设备管理平台", "description": "用于 OLT、PON 口、ONU 注册、网络设备状态等管理，不局限于单台 OLT。", "fields": ["network_mgmt_system_type", "olt_system_type", "olt_url", "olt_username", "olt_password"]},
            {"title": "IPTV 系统", "description": "用于 IPTV 账号、套餐、故障查询。暂不接入时可选择不接入。", "fields": ["iptv_system_type", "iptv_url", "iptv_username", "iptv_password"]},
            {"title": "工单系统", "description": "用于自动生成、派发、跟踪装维工单。", "fields": ["ticket_system_url", "ticket_username", "ticket_password"]},
            {"title": "通知通道接入", "description": "所有能力默认可使用这些通道，不按客服/装维/老板硬拆。", "fields": ["wechat_webhook_url", "feishu_webhook_url", "email_smtp_host", "email_smtp_port", "email_username", "email_password", "sms_provider", "sms_api_url", "sms_api_key"]},
            {"title": "业务通知规则", "description": "配置哪些业务事件需要通知，以及默认通知给谁。", "fields": ["isp_notify_channels", "isp_notify_contacts", "isp_notify_events", "default_renew_months"]},
        ]},
    },
    "ai-smart-monitor": {
        "cap_id": "ai-smart-monitor",
        "cap_name": "AI智能监控",
        "description": "接入摄像头、NVR、AI能力类型和事件通知规则。",
        "template": {"type": "object", "properties": {
            "camera_access_type": _field("select", "摄像头接入方式", default="onvif", options=[
                _option("onvif", "ONVIF 自动发现"),
                _option("rtsp", "RTSP 实时流"),
                _option("brand_direct", "品牌直连", "planned"),
            ]),
            "onvif_network": _field("string", "ONVIF 扫描网段", placeholder="例如：192.168.1.0/24"),
            "rtsp_url": _field("textarea", "RTSP 地址清单", placeholder="每行一个 RTSP 地址"),
            "nvr_system_type": _field("select", "NVR录像主机品牌", default="dahua", options=[
                _option("dahua", "大华 NVR", "planned"),
                _option("hikvision", "海康 NVR", "planned"),
                _option("generic_onvif_replay", "通用 ONVIF 回放"),
            ]),
            "nvr_url": _field("string", "NVR/录像平台地址"),
            "nvr_username": _field("string", "NVR账号"),
            "nvr_password": _field("password", "NVR密码", secret=True),
            "enabled_ai_capabilities": _field("multiselect", "AI能力类型", default=["realtime_alert", "recording_search"], options=[
                _option("realtime_alert", "实时告警"),
                _option("recording_search", "录像回查", "planned"),
                _option("person_search", "AI找人", "planned"),
                _option("throw_detection", "高空抛物"),
                _option("hygiene_patrol", "卫生巡检"),
            ]),
            "hygiene_notify_contacts": _field("textarea", "卫生巡检通知对象", placeholder="例如：清洁主管,138...,email"),
            "throw_notify_contacts": _field("textarea", "高空抛物通知对象", placeholder="例如：保安队长,138...,email"),
            "wechat_webhook_url": _field("password", "微信/企业微信 Webhook", secret=True),
            "feishu_webhook_url": _field("password", "飞书 Webhook", secret=True),
            "email_smtp_host": _field("string", "邮件 SMTP 地址"),
            "sms_api_url": _field("string", "短信接口地址"),
        }},
        "ui_schema": {"groups": [
            {"title": "摄像头接入", "description": "实时画面优先走 ONVIF/RTSP，特殊现场再做品牌直连。", "fields": ["camera_access_type", "onvif_network", "rtsp_url"]},
            {"title": "NVR录像主机", "description": "历史录像、录像回查、AI找人主要从 NVR 获取录像片段。", "fields": ["nvr_system_type", "nvr_url", "nvr_username", "nvr_password"]},
            {"title": "AI能力类型", "description": "AI找人属于录像回查之上的专项能力。", "fields": ["enabled_ai_capabilities"]},
            {"title": "事件通知规则", "description": "不同事件通知不同负责人。", "fields": ["hygiene_notify_contacts", "throw_notify_contacts"]},
            {"title": "通知通道接入", "description": "微信、飞书、邮件、短信统一接入。", "fields": ["wechat_webhook_url", "feishu_webhook_url", "email_smtp_host", "sms_api_url"]},
        ]},
    },
}


class LocalLogBuffer(logging.Handler):
    def __init__(self, capacity: int = 300):
        super().__init__()
        self.capacity = capacity
        self.rows: list[str] = []

    def emit(self, record):
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            self.rows.append(msg)
            if len(self.rows) > self.capacity:
                self.rows = self.rows[-self.capacity :]
        except Exception:
            pass

    def tail(self, limit: int = 120) -> list[str]:
        return self.rows[-limit:]


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>AgentHub 本地工作台</title>
<style>
:root{--ink:#111827;--muted:#667085;--line:#d8dee8;--bg:#f5f7fb;--brand:#0f172a;--ok:#067647;--warn:#b54708}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:14px/1.55 "Microsoft YaHei",Segoe UI,Arial,sans-serif;color:var(--ink)}
.wrap{max-width:1180px;margin:0 auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px}h1{font-size:22px;margin:0 0 4px}.hint{color:var(--muted);font-size:13px}.tabs{display:flex;gap:10px;margin:14px 0;flex-wrap:wrap}.tab,.btn{border:1px solid var(--line);background:#fff;border-radius:8px;padding:9px 15px;cursor:pointer;color:var(--ink);font-weight:600}.tab.active,.btn.primary{background:var(--brand);color:#fff;border-color:var(--brand)}.card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:18px;margin-bottom:16px}.toolbar{display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin:14px 0}.toolbar>div{min-width:240px;flex:1}label{display:block;font-weight:650;margin-bottom:7px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}input,select,textarea{width:100%;border:1px solid #cbd5e1;border-radius:8px;padding:10px 11px;background:#fff;color:var(--ink);font:inherit;min-height:42px}textarea{min-height:92px;resize:vertical}.form-section{border:1px solid #e5eaf2;background:#fff;border-radius:8px;margin:16px 0;padding:0}.section-head{padding:16px 18px;border-bottom:1px solid #edf1f7;background:#f8fafc}.section-head h3{margin:0;font-size:16px}.section-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.section-body{padding:18px}.field{min-width:0}.field .desc{margin-top:5px;color:var(--muted);font-size:12px}.checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}.check{display:flex;align-items:center;gap:8px;border:1px solid #d8dee8;border-radius:8px;padding:9px 10px;background:#fff}.check input{width:16px;min-height:16px}.badge{display:inline-flex;align-items:center;border-radius:999px;padding:1px 7px;font-size:12px;margin-left:6px}.trained{background:#dcfce7;color:#166534}.generic{background:#e0f2fe;color:#075985}.planned{background:#fef3c7;color:#92400e}.none{background:#f3f4f6;color:#4b5563}.pill{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:4px 10px;background:#fff;margin:3px;color:#344054}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.chatbox{height:360px;overflow:auto;border:1px solid #e1e7ef;border-radius:8px;background:#fafbfc;padding:12px}.msg{max-width:78%;padding:10px 12px;border-radius:8px;margin:9px 0;white-space:pre-wrap}.user{margin-left:auto;background:#111827;color:#fff}.bot{background:#fff;border:1px solid #dfe5ee}.log{background:#0b1220;color:#d6e2ff;border-radius:8px;padding:12px;height:260px;overflow:auto;font-family:Consolas,monospace;font-size:12px}.notice{border-radius:8px;padding:11px 12px;margin:12px 0}.notice.ok{background:#ecfdf3;color:var(--ok)}.notice.warn{background:#fffaeb;color:var(--warn)}@media(max-width:820px){.grid,.grid3{grid-template-columns:1fr}.wrap{padding:14px}.msg{max-width:96%}}
</style>
</head>
<body><div class="wrap">
<div class="top"><div><h1>AgentHub 本地工作台</h1><div class="hint">客户端按当前能力 API Key 从平台拉取配置模板；配置值保存在客户本地。</div></div><button class="btn" onclick="refresh(true)">刷新</button></div>
<div class="tabs"><button class="tab active" data-tab="status" onclick="showTab('status')">状态</button><button class="tab" data-tab="config" onclick="showTab('config')">本地配置</button><button class="tab" data-tab="chat" onclick="showTab('chat')">能力对话</button><button class="tab" data-tab="diag" onclick="showTab('diag')">安全诊断</button></div>
<section id="status" class="card page"></section>
<section id="config" class="card page" style="display:none"><h2>能力本地配置</h2><p class="hint">表单由平台配置模板驱动，按能力分组展示。新增能力上架后优先通过平台模板扩展，不再把所有配置写死进客户端。</p><div class="toolbar"><div><label>能力</label><select id="cfgCap" onchange="renderConfigForm()"></select></div><div><label>配置状态</label><input id="cfgState" disabled></div></div><div id="configForm"></div><div class="row" style="margin-top:16px"><button class="btn primary" onclick="saveConfig()">保存本地配置</button><button class="btn" onclick="testConnectivity()">测试连接</button><span id="cfgMsg" class="hint"></span></div></section>
<section id="chat" class="card page" style="display:none"><h2>能力对话</h2><p class="hint">选择已订阅能力后可在本地直接对话。ISP 客服会自动区分账号查询和光猫状态查询。</p><select id="chatCap"></select><div id="chatBox" class="chatbox"></div><div class="row" style="margin-top:10px"><textarea id="chatText" rows="3" placeholder="例如：查询账号 0755xxxx@163.gd 是否在线，或查这个账号的光猫状态"></textarea><button class="btn primary" onclick="sendChat()">发送</button></div></section>
<section id="diag" class="card page" style="display:none"><h2>安全诊断</h2><div id="diagBody" class="log"></div></section>
</div><script>
const token=new URL(location.href).searchParams.get('token')||'';let statusData=null,localConfigs={},templates={};
function showTab(id){document.querySelectorAll('.page').forEach(x=>x.style.display=x.id===id?'block':'none');document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===id));}
async function api(path,opts={}){const r=await fetch(path+(path.includes('?')?'&':'?')+'token='+encodeURIComponent(token),opts);return await r.json();}
function capName(id){return templates[id]?.cap_name||{'isp-smart-cs':'ISP智能客服','ai-smart-monitor':'AI智能监控'}[id]||id;}
function caps(){let ids=new Set();Object.keys(templates).forEach(x=>ids.add(x));(statusData?.plugins||[]).forEach(p=>ids.add(p.cap_id));(statusData?.authorized_capabilities||[]).forEach(c=>ids.add(c.cap_id));Object.keys(localConfigs).forEach(id=>ids.add(id));return [...ids].filter(Boolean);}
function isEditing(){return document.activeElement&&document.activeElement.closest&&document.activeElement.closest('#configForm,#bindKey,#chatText');}
async function refresh(force=false){statusData=await api('/api/status');if(force||!isEditing()){localConfigs=await api('/api/local-configs');templates=await api('/api/config-templates');renderStatus();fillCapSelects();if(force||!document.querySelector('#configForm [data-field]'))renderConfigForm();}loadLogs();}
function renderStatus(){const s=statusData||{};document.getElementById('status').innerHTML=`<h2>连接状态</h2><div class="grid3"><div><label>服务地址</label><input disabled value="${esc(s.server_url||'')}"></div><div><label>设备ID</label><input disabled value="${esc(s.device_id||'未连接')}"></div><div><label>状态</label><input disabled value="${s.connected?'已连接':'未连接'}"></div></div><div class="notice ${s.connected?'ok':'warn'}">${s.connected?'客户端已连接平台，可接收能力任务。':'客户端未连接平台，请确认 API Key 和网络。'}</div><h3>已识别能力</h3>${caps().map(id=>`<span class="pill">${esc(capName(id))}</span>`).join('')||'<span class="hint">尚未绑定能力 API Key</span>'}<h3 style="margin-top:18px">绑定能力 API Key</h3><div class="grid"><div><label>能力</label><select id="bindCap">${[...new Set([...caps(),'isp-smart-cs','ai-smart-monitor'])].map(id=>`<option value="${esc(id)}">${esc(capName(id))}</option>`).join('')}</select></div><div><label>API Key</label><input id="bindKey" type="password" placeholder="粘贴该能力订阅 Key"></div></div><div class="row" style="margin-top:12px"><button class="btn primary" onclick="bindKey()">保存绑定</button><span id="bindMsg" class="hint"></span></div>`;}
function fillCapSelects(){for(const id of ['cfgCap','chatCap']){const el=document.getElementById(id);const old=el.value;el.innerHTML=caps().map(c=>`<option value="${esc(c)}">${esc(capName(c))}</option>`).join('');if(old&&caps().includes(old))el.value=old;}}
async function bindKey(){const cap=document.getElementById('bindCap').value,key=document.getElementById('bindKey').value.trim();const res=await api('/api/bind-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cap_id:cap,api_key:key,server_url:statusData.server_url})});document.getElementById('bindMsg').textContent=res.success?'已保存':'保存失败';refresh(true);}
function renderConfigForm(){const cap=document.getElementById('cfgCap').value||caps()[0]||'isp-smart-cs',cfg=localConfigs[cap]||{},tpl=templates[cap]||{};document.getElementById('cfgState').value=Object.keys(cfg).length?'已填写':'未填写';const props=tpl.template?.properties||{},groups=tpl.ui_schema?.groups||[];let html='';if(tpl.source==='fallback')html+='<div class="notice warn">当前未能从平台拉取模板，已使用客户端内置备用模板。</div>';if(tpl.description)html+=`<div class="notice ok">${esc(tpl.description)}</div>`;if(groups.length){for(const g of groups){html+=`<section class="form-section"><div class="section-head"><h3>${esc(g.title||'配置分组')}</h3>${g.description?`<p>${esc(g.description)}</p>`:''}</div><div class="section-body"><div class="grid3">`;for(const key of g.fields||[]){if(props[key])html+=fieldHtml(key,props[key],cfg[key]);}html+='</div></div></section>';}}else{html='<section class="form-section"><div class="section-head"><h3>配置项</h3></div><div class="section-body"><div class="grid3">'+Object.entries(props).map(([k,f])=>fieldHtml(k,f,cfg[k])).join('')+'</div></div></section>';}document.getElementById('configForm').innerHTML=html;}
function fieldHtml(key,field,v){const val=v??field.default??'',title=field.title||key,desc=field.description||'';let input='',options=field.options||[];if(field.type==='select'){input=`<select data-field="${esc(key)}">${options.map(o=>`<option value="${esc(o.value)}" ${String(val)===String(o.value)?'selected':''}>${esc(o.label||o.value)}${o.status?`（${statusLabel(o.status)}）`:''}</option>`).join('')}</select>`;}else if(field.type==='multiselect'){const selected=Array.isArray(val)?val:String(val||'').split(',').filter(Boolean);input=`<div class="checks" data-field="${esc(key)}">${options.map(o=>`<label class="check"><input type="checkbox" name="field_${esc(key)}" value="${esc(o.value)}" ${selected.includes(o.value)?'checked':''}><span>${esc(o.label||o.value)}${o.status?` <span class="badge ${esc(o.status)}">${statusLabel(o.status)}</span>`:''}</span></label>`).join('')}</div>`;}else if(field.type==='textarea'){input=`<textarea data-field="${esc(key)}" placeholder="${esc(field.placeholder||'')}">${esc(val)}</textarea>`;}else{input=`<input data-field="${esc(key)}" type="${field.type==='password'?'password':field.type==='number'?'number':'text'}" value="${esc(val)}" placeholder="${esc(field.placeholder||'')}">`;}return `<div class="field"><label>${esc(title)}</label>${input}${desc?`<div class="desc">${esc(desc)}</div>`:''}</div>`;}
function collectConfig(){let cfg={};document.querySelectorAll('#configForm [data-field]').forEach(el=>{const k=el.dataset.field;if(el.classList.contains('checks'))cfg[k]=Array.from(el.querySelectorAll('input:checked')).map(x=>x.value);else cfg[k]=el.type==='number'?Number(el.value):el.value;});return cfg;}
async function saveConfig(){const cap=document.getElementById('cfgCap').value,cfg=collectConfig();const res=await api('/api/local-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cap_id:cap,config:cfg})});document.getElementById('cfgMsg').textContent=res.success?'已保存':'保存失败：'+(res.error||'');refresh(true);}
async function testConnectivity(){const cap=document.getElementById('cfgCap').value,res=await api('/api/local-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cap_id:cap,action:'test_connectivity',params:{}})});document.getElementById('cfgMsg').textContent=JSON.stringify(res.data||res);}
function addMsg(text,cls){const box=document.getElementById('chatBox'),div=document.createElement('div');div.className='msg '+cls;div.textContent=text;box.appendChild(div);box.scrollTop=box.scrollHeight;}
async function sendChat(){const cap=document.getElementById('chatCap').value,text=document.getElementById('chatText').value.trim();if(!text)return;addMsg(text,'user');document.getElementById('chatText').value='';const res=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cap_id:cap,text})});addMsg(res.message||JSON.stringify(res),'bot');}
async function loadLogs(){const res=await api('/api/logs');document.getElementById('diagBody').textContent=(res.logs||[]).join('\n');}
function statusLabel(s){return{trained:'已训练',generic:'通用',planned:'待适配',none:'不接入'}[s]||s;}function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
refresh(true);setInterval(()=>refresh(false),5000);
</script></body></html>"""


class LocalWorkbenchServer:
    def __init__(self, client, host: str = "127.0.0.1", port: int = 8765, on_bind=None, on_save_local_config=None, log_buffer=None):
        self.client = client
        self.host = host
        self.port = port
        self.on_bind = on_bind
        self.on_save_local_config = on_save_local_config
        self.log_buffer = log_buffer
        self.token = secrets.token_urlsafe(24)
        self.url = f"http://{host}:{port}/?token={self.token}"
        self._server = None
        self._thread = None

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def _auth(self):
                parsed = urlparse(self.path)
                return parse_qs(parsed.query).get("token", [""])[0] == parent.token

            def _json(self, payload, status=200):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _html(self):
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                if not length:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    return self._html()
                if not self._auth():
                    return self._json({"success": False, "error": "unauthorized"}, 403)
                if parsed.path == "/api/status":
                    return self._json(parent.client.get_status())
                if parsed.path == "/api/local-configs":
                    return self._json(getattr(parent.client, "_configs", {}))
                if parsed.path == "/api/config-templates":
                    return self._json(parent.get_config_templates())
                if parsed.path == "/api/logs":
                    logs = parent.log_buffer.tail() if parent.log_buffer else []
                    return self._json({"logs": logs})
                return self._json({"success": False, "error": "not found"}, 404)

            def do_POST(self):
                parsed = urlparse(self.path)
                if not self._auth():
                    return self._json({"success": False, "error": "unauthorized"}, 403)
                try:
                    data = self._read_json()
                    if parsed.path == "/api/bind-key":
                        if parent.on_bind:
                            parent.on_bind(data.get("api_key", ""), data.get("server_url") or parent.client.server_url, data.get("cap_id", ""))
                        return self._json({"success": True})
                    if parsed.path == "/api/local-config":
                        cap_id = data.get("cap_id") or ""
                        config = data.get("config") or {}
                        saved = parent.on_save_local_config(cap_id, config) if parent.on_save_local_config else config
                        return self._json({"success": True, "config": saved})
                    if parsed.path == "/api/local-action":
                        result = asyncio.run(parent.client.execute_local(data.get("cap_id"), data.get("action"), data.get("params") or {}))
                        return self._json(result)
                    if parsed.path == "/api/chat":
                        result = asyncio.run(parent._chat(data.get("cap_id"), data.get("text") or ""))
                        return self._json(result)
                    return self._json({"success": False, "error": "not found"}, 404)
                except Exception as exc:
                    logger.exception("Workbench request failed")
                    return self._json({"success": False, "error": str(exc)}, 500)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Local workbench started: %s", self.url)

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def _http_server_url(self) -> str:
        url = self.client.server_url.rstrip("/")
        if url.startswith("wss://"):
            return "https://" + url[6:]
        if url.startswith("ws://"):
            return "http://" + url[5:]
        return url

    def get_config_templates(self) -> dict:
        result = {}
        keys = getattr(self.client, "capability_api_keys", {}) or {}
        cap_ids = set(keys.keys()) | set(getattr(self.client, "_configs", {}).keys()) | {"isp-smart-cs", "ai-smart-monitor"}
        for cap_id in cap_ids:
            template = self._fetch_platform_template(cap_id, keys.get(cap_id) or self.client.api_key)
            result[cap_id] = template or {**FALLBACK_TEMPLATES.get(cap_id, {"cap_id": cap_id, "cap_name": CAP_NAMES.get(cap_id, cap_id), "template": {"properties": {}}, "ui_schema": {"groups": []}}), "source": "fallback"}
        return result

    def _fetch_platform_template(self, cap_id: str, api_key: str) -> dict | None:
        if not api_key:
            return None
        try:
            url = f"{self._http_server_url()}/api/cap-config/client-template/{cap_id}"
            with httpx.Client(timeout=6, verify=False) as client:
                resp = client.get(url, params={"api_key": api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    data["source"] = "platform"
                    return data
        except Exception as exc:
            logger.debug("Fetch platform template failed: %s", exc)
        return None

    async def _chat(self, cap_id: str, text: str) -> dict:
        cap_id = cap_id or "isp-smart-cs"
        if cap_id != "isp-smart-cs":
            return {"success": False, "message": "该能力的本地对话执行器还在接入中。"}
        account = self._extract_keyword(text)
        if not account:
            return {"success": False, "message": "请提供要查询的宽带账号、手机号、SN 或 MAC。"}
        action = "query_onu_status" if any(word in text for word in ["光猫", "ONU", "猫", "信号", "光功率"]) else "query_account"
        result = await self.client.execute_local(cap_id, action, {"account": account, "query_type": "status"})
        return {"success": bool(result.get("success")), "message": self._format_isp_result(action, result), "raw": result}

    @staticmethod
    def _extract_keyword(text: str) -> str:
        patterns = [r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", r"(?<!\d)1\d{10}(?!\d)", r"(?<!\d)\d{7,14}(?!\d)", r"[A-Fa-f0-9]{12,}"]
        for pattern in patterns:
            match = re.search(pattern, text or "")
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _format_isp_result(action: str, result: dict) -> str:
        if not result.get("success"):
            return result.get("error") or "查询失败，请检查账号或本地系统配置。"
        data = result.get("data") or {}
        if action == "query_onu_status":
            return f"光猫在线：{'是' if data.get('online') else '否'}\nSN：{data.get('sn') or '-'}\n型号：{data.get('manufacturer') or ''} {data.get('model') or ''}\n下行光功率：{(data.get('optical') or {}).get('rx_power') or '-'} dBm\nPPPoE：{(data.get('pppoe') or {}).get('status') or '-'}"
        users = data.get("users") or []
        if not users:
            return "未找到该账号。"
        u = users[0]
        return f"账号：{u.get('account') or '-'}\n姓名：{u.get('name') or '-'}\n套餐：{u.get('package') or '-'}\n在线：{'是' if u.get('online') else '否'}\n停机：{'是' if u.get('paused') else '否'}\n到期：{u.get('expire_time') or '-'}\n地址：{u.get('address') or '-'}"
