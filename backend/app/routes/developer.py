"""Developer routes: capability management, earnings, analytics"""
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import get_db, Capability, CapabilityVersion, CallLog, User
from ..auth import get_current_user
from ..config import CAPABILITIES_DIR

router = APIRouter(prefix="/developer", tags=["developer"])


class CapabilityCreate(BaseModel):
    cap_id: str
    name: str
    description: str = ""
    long_description: str = ""
    category: str = "isp"
    subcategory: str = ""
    level: str = "atomic"  # atomic / composite
    dependencies: list[str] = []  # cap_ids this capability orchestrates
    tags: list[str] = []
    pricing_model: str = "per_call"
    price: float = 0.1
    llm_mode: str = "platform"
    runtime_config: dict = {}
    interfaces_config: dict = {}


class CapabilityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    long_description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    level: str | None = None
    dependencies: list[str] | None = None
    tags: list[str] | None = None
    pricing_model: str | None = None
    price: float | None = None
    runtime_config: dict | None = None
    interfaces_config: dict | None = None


# ---- Capability CRUD ----

@router.get("/capabilities")
def list_my_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all capabilities by current developer"""
    caps = db.query(Capability).filter(
        Capability.developer_id == current_user.id
    ).order_by(Capability.created_at.desc()).all()

    def parse_json(value, fallback):
        if not value:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback

    return [{
        "id": c.id,
        "cap_id": c.cap_id,
        "name": c.name,
        "version": c.version,
        "description": c.description,
        "long_description": c.long_description,
        "category": c.category,
        "subcategory": c.subcategory,
        "level": c.level,
        "tags": parse_json(c.tags, []),
        "dependencies": parse_json(c.dependencies, []),
        "status": c.status,
        "pricing_model": c.pricing_model,
        "price": c.price,
        "call_count": c.call_count,
        "avg_rating": c.avg_rating,
        "created_at": c.created_at,
    } for c in caps]


@router.post("/capabilities")
def create_capability(
    req: CapabilityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new capability"""
    if current_user.role not in ("developer", "admin"):
        raise HTTPException(403, "Only developers can create capabilities")

    # Check unique cap_id
    if db.query(Capability).filter(Capability.cap_id == req.cap_id).first():
        raise HTTPException(400, f"Capability ID '{req.cap_id}' already exists")

    now = datetime.now(timezone.utc).isoformat()
    cap = Capability(
        developer_id=current_user.id,
        cap_id=req.cap_id,
        name=req.name,
        description=req.description,
        long_description=req.long_description,
        category=req.category,
        subcategory=req.subcategory,
        level=req.level,
        dependencies=json.dumps(req.dependencies),
        tags=json.dumps(req.tags),
        status="draft",
        pricing_model=req.pricing_model,
        price=req.price,
        llm_mode=req.llm_mode,
        runtime_config=json.dumps(req.runtime_config),
        interfaces_config=json.dumps(req.interfaces_config),
        created_at=now,
        updated_at=now,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)

    # Create capability directory
    cap_dir = CAPABILITIES_DIR / req.cap_id
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "agent").mkdir(exist_ok=True)
    (cap_dir / "agent" / "knowledge").mkdir(exist_ok=True)
    (cap_dir / "agent" / "tools").mkdir(exist_ok=True)

    return {"id": cap.id, "cap_id": cap.cap_id, "status": "draft"}


@router.put("/capabilities/{cap_id}")
def update_capability(
    cap_id: str,
    req: CapabilityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update capability metadata"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.developer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Not your capability")

    if cap.status not in ("draft", "rejected"):
        raise HTTPException(400, "Can only edit draft or rejected capabilities")

    updates = req.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key in ("tags", "dependencies"):
            setattr(cap, key, json.dumps(value))
        elif key in ("runtime_config", "interfaces_config"):
            setattr(cap, key, json.dumps(value))
        else:
            setattr(cap, key, value)

    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "ok"}


@router.post("/capabilities/{cap_id}/submit")
def submit_for_review(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit capability for review"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.developer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Not your capability")
    if cap.status not in ("draft", "rejected"):
        raise HTTPException(400, f"Cannot submit from status '{cap.status}'")

    cap.status = "submitted"
    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "submitted"}


@router.post("/capabilities/{cap_id}/versions")
async def upload_version(
    cap_id: str,
    version: str = Form(...),
    changelog: str = Form(""),
    package: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a new version package"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.developer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Not your capability")

    import hashlib
    content = await package.read()
    checksum = hashlib.sha256(content).hexdigest()

    # Save package
    pkg_dir = Path(f"/opt/agenthub/data/packages/{cap_id}")
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_path = pkg_dir / f"v{version}.tar.gz"
    with open(pkg_path, "wb") as f:
        f.write(content)

    ver = CapabilityVersion(
        capability_id=cap.id,
        version=version,
        package_path=str(pkg_path),
        checksum=checksum,
        changelog=changelog,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(ver)
    cap.version = version
    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    return {"version": version, "checksum": checksum}


# ---- Earnings ----

@router.get("/earnings")
def earnings_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get earnings overview"""
    if current_user.role not in ("developer", "admin"):
        raise HTTPException(403, "Developers only")

    # Calculate from call logs through capabilities
    dev_caps = db.query(Capability).filter(Capability.developer_id == current_user.id).all()
    cap_ids = [c.id for c in dev_caps]

    total_charged = 0
    month_charged = 0
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()

    if cap_ids:
        total_charged = db.query(func.sum(CallLog.charged)).filter(
            CallLog.capability_id.in_(cap_ids),
            CallLog.status == "success",
        ).scalar() or 0
        month_charged = db.query(func.sum(CallLog.charged)).filter(
            CallLog.capability_id.in_(cap_ids),
            CallLog.status == "success",
            CallLog.created_at >= month_start,
        ).scalar() or 0

    # 70% developer cut
    total_earnings = float(total_charged) * 0.70
    month_earnings = float(month_charged) * 0.70

    return {
        "total_earnings": round(total_earnings, 2),
        "month_earnings": round(month_earnings, 2),
        "available": round(current_user.earnings, 2),
        "capability_count": len(dev_caps),
    }


@router.get("/earnings/detail")
def earnings_detail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-capability earnings breakdown"""
    dev_caps = db.query(Capability).filter(Capability.developer_id == current_user.id).all()
    result = []
    for cap in dev_caps:
        total = db.query(func.sum(CallLog.charged)).filter(
            CallLog.capability_id == cap.id,
            CallLog.status == "success",
        ).scalar() or 0
        calls = db.query(func.count(CallLog.id)).filter(
            CallLog.capability_id == cap.id,
            CallLog.status == "success",
        ).scalar() or 0
        result.append({
            "cap_id": cap.cap_id,
            "name": cap.name,
            "total_calls": calls,
            "total_charged": round(float(total), 2),
            "developer_share": round(float(total) * 0.70, 2),
        })
    return result


@router.post("/withdraw")
def request_withdrawal(
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request a withdrawal"""
    if current_user.role not in ("developer", "admin"):
        raise HTTPException(403, "Developers only")
    if amount < 100:
        raise HTTPException(400, "Minimum withdrawal is 100 yuan")
    if amount > current_user.earnings:
        raise HTTPException(400, "Insufficient available earnings")

    from ..models import Withdrawal
    w = Withdrawal(
        developer_id=current_user.id,
        amount=amount,
        applied_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(w)
    current_user.earnings -= amount
    db.commit()
    return {"withdrawal_id": w.id, "amount": amount, "status": "pending"}


@router.get("/analytics")
def analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Basic analytics for developer's capabilities"""
    dev_caps = db.query(Capability).filter(Capability.developer_id == current_user.id).all()
    cap_ids = [c.id for c in dev_caps]

    # Last 30 days daily calls
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    daily = []
    for i in range(30, 0, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        next_day = (now - timedelta(days=i-1)).strftime("%Y-%m-%d")
        count = 0
        if cap_ids:
            count = db.query(func.count(CallLog.id)).filter(
                CallLog.capability_id.in_(cap_ids),
                CallLog.created_at >= day,
                CallLog.created_at < next_day,
            ).scalar() or 0
        daily.append({"date": day, "calls": count})

    return {
        "total_capabilities": len(dev_caps),
        "published": len([c for c in dev_caps if c.status == "published"]),
        "daily_calls": daily,
    }
