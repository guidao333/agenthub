"""AgentHub Configuration"""
import os
from pathlib import Path

# Base paths - allow override for local dev
_BASE_DEV = os.getenv("AGENTHUB_DEV", "")  # 本地开发用 AGENTHUB_DEV=1
BASE_DIR = Path("/opt/agenthub") if not _BASE_DEV else Path(".").resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CAPABILITIES_DIR = BASE_DIR / "capabilities"
BACKUP_DIR = BASE_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"

# Create dirs
for d in [DATA_DIR, CAPABILITIES_DIR, BACKUP_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/agenthub.db")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "agenthub-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

# LLM
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# Token pricing (per 1K tokens, CNY)
LLM_INPUT_PRICE_PER_1K = 0.001  # ¥0.001/千输入token
LLM_OUTPUT_PRICE_PER_1K = 0.002  # ¥0.002/千输出token
LLM_COST_MULTIPLIER = 1.2  # 含冗余

# Pricing
PLATFORM_CUT_RATE = 0.30  # 30% platform cut (含 LLM 成本)
DEVELOPER_CUT_RATE = 0.70  # 70% developer cut
SELF_KEY_PLATFORM_CUT = 0.15  # 15% when developer uses own LLM key
SELF_KEY_DEVELOPER_CUT = 0.85

# Free trial
NEW_USER_BONUS = 5.0  # ¥5 赠送余额
FREE_TRIAL_PER_CAP = 3  # 每个能力每天 3 次试用

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60

# Chat engine
MAX_TOOL_CALL_ROUNDS = 5
MAX_CONTEXT_TURNS = 10
CAPABILITY_TIMEOUT_SECONDS = 30
BRIDGE_SESSION_TIMEOUT_MINUTES = 30
BRIDGE_EXEC_TIMEOUT_SECONDS = 60

# Sandbox
SANDBOX_MEMORY_LIMIT_MB = 256
SANDBOX_CPU_TIME_SECONDS = 30
SANDBOX_FILE_SIZE_MB = 10

# Health monitor
HEALTH_CHECK_INTERVAL_SECONDS = 300  # 5 min
HEALTH_ERROR_RATE_DEGRADED = 0.05
HEALTH_ERROR_RATE_DOWN = 0.20
HEALTH_DEGRADED_THRESHOLD = 3  # 连续 3 次降级发告警
HEALTH_DOWN_THRESHOLD = 5  # 连续 5 次降级自动暂停

# Monitor email (via QQ SMTP)
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "5690300@qq.com"
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL = "460552193@qq.com"
