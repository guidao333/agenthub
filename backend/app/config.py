"""AgentHub Configuration"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path("/opt/agenthub")
DATA_DIR = BASE_DIR / "data"
CAPABILITIES_DIR = DATA_DIR / "capabilities"
UPLOADS_DIR = DATA_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/agenthub.db")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "agenthub-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# LLM
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# Pricing
PLATFORM_CUT_RATE = 0.30  # 30% platform cut
DEVELOPER_CUT_RATE = 0.70  # 70% developer cut
SELF_KEY_PLATFORM_CUT = 0.15  # 15% when developer uses own LLM key
SELF_KEY_DEVELOPER_CUT = 0.85

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60

# Chat engine
MAX_TOOL_CALL_ROUNDS = 5
MAX_CONTEXT_TURNS = 10
CAPABILITY_TIMEOUT_SECONDS = 30
