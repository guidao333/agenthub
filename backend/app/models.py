"""Database models and session management"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Text as JSONText
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
    balance = Column(Float, default=0.0)
    earnings = Column(Float, default=0.0)
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
    tags = Column(Text)  # JSON array
    description = Column(Text)
    long_description = Column(Text)
    status = Column(String(20), default="draft", index=True)
    pricing_model = Column(String(20))  # per_call / monthly / freemium / bundle
    price = Column(Float, default=0.0)
    llm_mode = Column(String(20), default="platform")
    runtime_config = Column(Text)  # JSON
    interfaces_config = Column(Text)  # JSON
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
    started_at = Column(String(30), default="")
    expires_at = Column(String(30), default="")


class CallLog(Base):
    __tablename__ = "call_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, index=True)
    capability_id = Column(Integer, index=True)
    session_id = Column(String(36))
    input_summary = Column(Text)
    output_summary = Column(Text)
    tool_calls = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    status = Column(String(20))  # success / error / timeout
    charged = Column(Float, default=0.0)
    created_at = Column(String(30), default="")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String(20))  # charge / payout
    amount = Column(Float)
    status = Column(String(20), default="pending")
    period_start = Column(String(30))
    period_end = Column(String(30))
    detail = Column(Text)  # JSON
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
    context = Column(Text)  # JSON: conversation history
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")


def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
