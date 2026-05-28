# AgentHub 项目指南

> 本文件是 Claude Code 的工作指南，启动时自动加载。

## 项目定位

AgentHub 是一个 **AI 能力模块交易平台**（类似 App Store）：
- 客户（ISP/物业/企业）按月订阅 AI 能力
- 开发者上架能力，平台 20% 抽成
- **核心架构**：对话在平台，推理在平台，执行在客户端

当前 2 个核心能力：
| 能力 | cap_id | 月付 | 说明 |
|------|--------|------|------|
| ISP 智能客服 | `isp-smart-cs` | ¥499 | 集成计费/OLT/TR069/IPTV |
| AI 智能监控 | `ai-smart-monitor` | ¥990 | 接入各品牌摄像头+NVR |

## 技术架构

```
前端: Vue3 + Vite + Tailwind CSS
后端: FastAPI + SQLite + SQLAlchemy
AI引擎: DeepSeek Function Calling
客户端通信: WebSocket 长连接
边缘端: Python + YOLOv8 + RTSP/ONVIF
```

## 目录结构

```
backend/
  app/
    routes/        # FastAPI 路由（14个模块）
      auth.py            # 用户认证
      market.py          # 能力市场
      billing.py         # 计费订阅
      admin.py           # 管理后台
      developer.py       # 开发者中心
      vision.py          # AI视觉API（11条）
      ws_client.py       # WebSocket通信层
      cap_config.py      # 能力配置表单
      cap_chat_engine.py # 统一能力对话引擎
      chat.py            # 通用对话
      dashboard.py       # 控制台
      config.py          # 系统配置
      bridge.py          # 桥接
      api_call.py        # API调用统计
    services/      # 业务逻辑
    middleware/    # 中间件（限频/日志/错误处理）
    models.py      # 数据模型
    auth.py        # 认证逻辑
    config.py      # 配置
    main.py        # 入口
frontend/
  src/             # Vue3 SPA 源码
  cap-config.html  # 独立能力配置页
  cap-chat.html    # 独立能力对话页
client/            # 统一客户端（WebSocket + 能力插件）
  plugins/         # 能力插件目录
edge/              # AI视觉边缘端（ONVIF/RTSP/YOLOv8）
docs/              # 规划文档（Codex 写的）
scripts/           # 部署脚本
```

## 服务器信息

| 项目 | 值 |
|------|-----|
| 服务器 | 183.11.239.100:2222（SSH: `ssh agenthub`） |
| 系统 | Debian 13 |
| 后端 | FastAPI :8000，systemd `agenthub.service` |
| 前端 | `/opt/agenthub/frontend/` |
| 数据库 | `/opt/agenthub/data/agenthub.db` |
| 域名 | www.agenthub.wang（Cloudflare Tunnel） |
| 管理员 | admin / admin123 |

## 工作分工

**两个 AI 协作开发，通过 Git 分支隔离：**

| 工具 | 分支 | 负责领域 |
|------|------|---------|
| Codex | `main` 或自己的分支 | 后端 Python + 客户端 + 边缘端 |
| **Claude Code** | `claude-code` | **前端 Vue3 + 新功能 + bug 修复** |

### 规则
1. **只在自己的分支提交**，不直接 push main
2. 改完后告知小新（啊锋的助手），由小新 review 后合并
3. 不要改 Codex 正在改的文件，有冲突找小新协调
4. 每次开始工作前 `git pull origin main` 同步最新代码

## 当前待办（Claude Code 负责）

### P0 — 必须先做
- [ ] 前端敏感信息治理：不显示 AI 模型名、内部 Key、供应商密钥
- [ ] 订阅到使用闭环优化：订阅后 → 配置能力 → 下载客户端 → 复制 API Key → 打开对话，全流程顺畅
- [ ] 独立页面（cap-config.html / cap-chat.html）统一到 Vue 路由

### P1 — 产品能力
- [ ] 开发者入驻介绍页 + 入驻协议 + 能力发布规则
- [ ] 控制台增加能力运行状态、客户端在线状态
- [ ] 前端能力详情页增加演示视频/截图位
- [ ] AI 监控通知规则前端配置（按事件/摄像头/时间段）

### P2 — 体验优化
- [ ] 移动端适配
- [ ] 深色模式
- [ ] 前端国际化（i18n）

## 编码规范
- 前端：Vue3 Composition API + TypeScript
- 样式：Tailwind CSS，不写自定义 CSS（除非必须）
- 组件：按功能模块划分，状态管理用 Pinia
- 提交信息：中文，简洁描述做了什么

## 常用命令
```bash
# 前端开发
cd frontend && npm run dev

# 前端构建
cd frontend && npm run build

# 同步代码
git fetch origin && git rebase origin/main
```
