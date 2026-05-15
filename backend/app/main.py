"""AgentHub FastAPI Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import init_db
from .routes import auth, market, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables"""
    init_db()
    # Create default admin user if not exists
    from .models import SessionLocal, User
    from .auth import hash_password
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            email="admin@agenthub.local",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)
        db.commit()
    db.close()
    print("AgentHub started - database initialized")
    yield


app = FastAPI(
    title="AgentHub",
    description="Agent Capability Marketplace Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    return {"name": "AgentHub", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
