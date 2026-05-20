"""AgentHub FastAPI Application v2.0"""

import time
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from .config import (
    DEEPSEEK_API_KEY, DATA_DIR, LOGS_DIR, SMTP_USER, SMTP_PASS,
    HEALTH_CHECK_INTERVAL_SECONDS,
)
from .models import init_db
from .middleware.request_log import request_logging
from .middleware.rate_limit import rate_limit_middleware, rate_limiter
from .middleware.error_handler import error_handler
from .routes import auth, market, chat, developer, admin, admin_manage, dashboard, api_call, config, billing, bridge, vision

# ── Logging ──
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOGS_DIR / "agenthub.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agenthub")

# ── Health Monitor (background) ──
_health_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown"""
    # ── Startup ──
    init_db()
    logger.info(f"✓ Database initialized at {DATA_DIR}/agenthub.db")
    logger.info(f"✓ AgentHub v2.0 started")

    yield

    # ── Shutdown ──
    logger.info("AgentHub shutting down")


# ── FastAPI App ──
app = FastAPI(
    title="AgentHub",
    description="Agent Capability Marketplace Platform v2.0",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handler ──
app.add_exception_handler(Exception, error_handler)

# ── Middleware (order matters: bottom runs first) ──
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(request_logging)

# ── Routes ──
app.include_router(auth.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(bridge.router, prefix="/api/v1/bridge")
app.include_router(developer.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_manage.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(api_call.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(vision.router, prefix="/api")

# Init vision tables
from .routes.vision import init_vision_tables as _init_vision
_init_vision()


# ── Root ──
@app.get("/")
def root():
    return {
        "name": "AgentHub",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "site": "https://www.agenthub.wang",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "llm_configured": bool(DEEPSEEK_API_KEY),
    }
