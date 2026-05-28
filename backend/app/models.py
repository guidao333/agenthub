"""Database models and session management (v2.0)"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False)  # customer / developer / admin
    balance = Column(Float, default=0.0)                     # 可用余额
    frozen_balance = Column(Float, default=0.0)              # 🔒 冻结中的金额
    earnings = Column(Float, default=0.0)                    # 开发者可提现余额
    free_quota_used = Column(Text, default="{}")             # 🔒 JSON: {cap_id: today_count}
    status = Column(String(20), default="active")
    created_at = Column(String(30), default="")


class Capability(Base):
    __tablename__ = "capabilities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    developer_id = Column(Integer, nullable=False, index=True)
    cap_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(String(20), default="1.0.0")
    category = Column(String(50))
    subcategory = Column(String(50))
    level = Column(String(20), default="atomic")            # atomic / composite
    tags = Column(Text)                                      # JSON array
    description = Column(Text)
    long_description = Column(Text)
    status = Column(String(20), default="draft", index=True) # draft/submitted/approved/rejected/published/suspended
    pricing_model = Column(String(20))                       # per_call / monthly / freemium / bundle
    price = Column(Float, default=0.0)
    llm_mode = Column(String(20), default="platform")        # platform / self_key
    runtime_config = Column(Text)                            # JSON
    interfaces_config = Column(Text)                         # JSON
    dependencies = Column(Text, default="[]")                # 🔒 JSON: [{cap_id, version, required}]
    grayscale = Column(Float, default=1.0)                   # 🔒 灰度比例 0.0~1.0
    health_status = Column(String(20), default="healthy")    # 🔒 healthy/degraded/down
    encrypted = Column(Integer, default=0)                   # 🔒 能力包是否加密存储
    review_checklist = Column(Text)                          # 🔒 JSON: 审核检查清单结果
    download_count = Column(Integer, default=0)
    call_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")
    published_at = Column(String(30), default="")


class CapabilityVersion(Base):
    __tablename__ = "capability_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    capability_id = Column(Integer, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    package_path = Column(String(500))
    checksum = Column(String(64))
    changelog = Column(Text)
    created_at = Column(String(30), default="")


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    capability_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default="active")
    api_key = Column(String(64), unique=True, index=True)
    locked_version = Column(String(20))                      # 🔒 锁定的版本，NULL=跟随最新
    started_at = Column(String(30), default="")
    expires_at = Column(String(30), default="")


class CallLog(Base):
    __tablename__ = "call_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, index=True)
    capability_id = Column(Integer, index=True)
    customer_id = Column(Integer, index=True)
    session_id = Column(String(36))
    trace_id = Column(String(64), index=True)                # 🔒 调用链追踪
    parent_call_id = Column(Integer, default=0)              # 🔒 父调用（组合能力）
    mode = Column(String(20), default="cloud")               # 🔒 cloud / bridge
    input_summary = Column(Text)
    output_summary = Column(Text)
    tool_calls = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    status = Column(String(20))                              # success / error / timeout
    charged = Column(Float, default=0.0)
    created_at = Column(String(30), default="")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String(20))                                # charge / payout
    amount = Column(Float)
    status = Column(String(20), default="pending")
    period_start = Column(String(30))
    period_end = Column(String(30))
    detail = Column(Text)
    created_at = Column(String(30), default="")


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    developer_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float)
    status = Column(String(20), default="pending")
    applied_at = Column(String(30), default="")
    processed_at = Column(String(30), default="")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    capability_id = Column(Integer, nullable=False)
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(String(30), default="")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    capability_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default="active")
    context = Column(Text)
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")


class CustomerConfig(Base):
    """客户配置（加密存储）"""
    __tablename__ = "customer_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    config_key = Column(String(100), nullable=False)
    config_value = Column(Text, nullable=False)
    encrypted = Column(Integer, default=1)
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")


class Webhook(Base):
    """Webhook 配置"""
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    url = Column(String(500), nullable=False)
    events = Column(Text, default="[]")
    secret = Column(String(64))
    status = Column(String(20), default="active")
    created_at = Column(String(30), default="")


class Announcement(Base):
    """系统公告"""
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    type = Column(String(20), default="info")
    target = Column(String(20), default="all")
    created_at = Column(String(30), default="")
    expires_at = Column(String(30), default="")


class BridgeSession(Base):
    """桥接会话"""
    __tablename__ = "bridge_sessions"
    id = Column(String(36), primary_key=True)
    customer_id = Column(Integer, nullable=False, index=True)
    capability_id = Column(Integer, nullable=False)
    status = Column(String(20), default="active")
    allowed_tools = Column(Text, default="[]")               # JSON: 允许的工具白名单
    context = Column(Text)                                   # JSON: 对话上下文 + 工具调用历史
    last_activity = Column(BigInteger, default=0)            # 时间戳 ms
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")


class Category(Base):
    """能力分类"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cat_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    icon = Column(String(20), default='')
    color = Column(String(20), default='#6B7280')
    description = Column(Text, default='')
    sort_order = Column(Integer, default=0)
    parent_id = Column(Integer, default=0)  # 0=顶级分类, >0=子分类的parent id
    created_at = Column(String(30), default='')
    updated_at = Column(String(30), default='')


def init_db():
    """Create all tables"""
    from .utils.helpers import now_timestamp
    from .auth import hash_password
    Base.metadata.create_all(bind=engine)

    # 创建默认管理员
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@agenthub.wang",
                password_hash=hash_password("admin123"),
                role="admin",
                balance=0,
                created_at=now_timestamp(),
            )
            db.add(admin)
            db.commit()
        _sync_builtin_capability_metadata(db)
    finally:
        db.close()


def _sync_builtin_capability_metadata(db):
    """Keep official capability metadata aligned after deployments."""

    changed = False
    builtin_prices = {
        "isp-smart-cs": {"pricing_model": "monthly", "price": 499.0},
        "ai-smart-monitor": {"pricing_model": "monthly", "price": 990.0},
    }
    for cap_id, meta in builtin_prices.items():
        cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
        if not cap:
            continue
        if cap.pricing_model != meta["pricing_model"]:
            cap.pricing_model = meta["pricing_model"]
            changed = True
        if float(cap.price or 0) != meta["price"]:
            cap.price = meta["price"]
            changed = True
    if changed:
        db.commit()


def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
