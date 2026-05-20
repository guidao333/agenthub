"""Admin category & capability management routes"""
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import (
    get_db, Capability, User, Base, engine, SessionLocal
)
from ..auth import require_role

router = APIRouter(prefix="/admin", tags=["admin-manage"])
admin_required = require_role("admin")


# ═══════════════════════════════════════════
# 分类管理
# ═══════════════════════════════════════════

class CategoryCreate(BaseModel):
    cat_id: str
    name: str
    icon: str = ""
    color: str = "#6B7280"
    description: str = ""
    parent_id: int = 0
    sort_order: int = 0

class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    description: str | None = None
    sort_order: int | None = None
    parent_id: int | None = None


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Get full category tree (public, no auth)"""
    from ..models import Category
    parents = db.query(Category).filter(Category.parent_id == 0).order_by(Category.sort_order).all()
    result = []
    for p in parents:
        subs = db.query(Category).filter(Category.parent_id == p.id).order_by(Category.sort_order).all()
        # Count capabilities
        cap_count = db.query(func.count(Capability.id)).filter(
            Capability.category == p.cat_id, Capability.status == "published"
        ).scalar() or 0
        sub_list = []
        for s in subs:
            sc = db.query(func.count(Capability.id)).filter(
                Capability.subcategory == s.cat_id, Capability.status == "published"
            ).scalar() or 0
            sub_list.append({
                "id": s.cat_id, "name": s.name, "description": s.description,
                "icon": s.icon, "sort_order": s.sort_order, "count": sc, "db_id": s.id,
            })
        result.append({
            "id": p.cat_id, "name": p.name, "icon": p.icon, "color": p.color,
            "description": p.description, "sort_order": p.sort_order,
            "count": cap_count, "db_id": p.id, "subcategories": sub_list,
        })
    return result


@router.post("/categories")
def create_category(
    req: CategoryCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    from ..models import Category
    if db.query(Category).filter(Category.cat_id == req.cat_id).first():
        raise HTTPException(400, f"Category ID '{req.cat_id}' already exists")
    now = datetime.now(timezone.utc).isoformat()
    cat = Category(
        cat_id=req.cat_id, name=req.name, icon=req.icon, color=req.color,
        description=req.description, sort_order=req.sort_order,
        parent_id=req.parent_id, created_at=now, updated_at=now,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "cat_id": cat.cat_id, "name": cat.name}


@router.put("/categories/{cat_id}")
def update_category(
    cat_id: str,
    req: CategoryUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    from ..models import Category
    cat = db.query(Category).filter(Category.cat_id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(cat, k, v)
    cat.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "ok"}


@router.delete("/categories/{cat_id}")
def delete_category(
    cat_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    from ..models import Category
    cat = db.query(Category).filter(Category.cat_id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    # Check for capabilities in this category
    cap_count = db.query(func.count(Capability.id)).filter(
        (Capability.category == cat_id) | (Capability.subcategory == cat_id)
    ).scalar()
    if cap_count > 0:
        raise HTTPException(400, f"Category has {cap_count} capabilities, move them first")
    # Delete children
    db.query(Category).filter(Category.parent_id == cat.id).delete()
    db.delete(cat)
    db.commit()
    return {"status": "deleted"}


# ═══════════════════════════════════════════
# 管理端能力 CRUD
# ═══════════════════════════════════════════

class AdminCapCreate(BaseModel):
    cap_id: str
    name: str
    description: str = ""
    long_description: str = ""
    category: str = ""
    subcategory: str = ""
    level: str = "atomic"
    tags: list[str] = []
    pricing_model: str = "per_call"
    price: float = 0.0
    developer_id: int | None = None  # optional: assign to a developer

class AdminCapUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    long_description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    level: str | None = None
    tags: list[str] | None = None
    pricing_model: str | None = None
    price: float | None = None
    status: str | None = None  # published / suspended / draft
    version: str | None = None


@router.get("/capabilities")
def admin_list_capabilities(
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Admin list ALL capabilities with filters"""
    q = db.query(Capability)
    if status:
        q = q.filter(Capability.status == status)
    if category:
        q = q.filter(Capability.category == category)
    if search:
        q = q.filter(Capability.name.contains(search) | Capability.cap_id.contains(search))

    total = q.count()
    caps = q.order_by(Capability.created_at.desc()).offset((page-1)*size).limit(size).all()

    items = []
    for c in caps:
        dev = db.query(User).filter(User.id == c.developer_id).first()
        items.append({
            "id": c.id, "cap_id": c.cap_id, "name": c.name,
            "description": c.description[:80] if c.description else "",
            "category": c.category, "subcategory": c.subcategory,
            "level": c.level, "version": c.version,
            "status": c.status, "pricing_model": c.pricing_model, "price": c.price,
            "call_count": c.call_count, "avg_rating": c.avg_rating,
            "developer": dev.username if dev else "unknown",
            "developer_id": c.developer_id,
            "created_at": c.created_at, "published_at": c.published_at,
        })
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/capabilities")
def admin_create_capability(
    req: AdminCapCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Admin directly create and publish a capability"""
    if db.query(Capability).filter(Capability.cap_id == req.cap_id).first():
        raise HTTPException(400, f"cap_id '{req.cap_id}' already exists")

    dev_id = req.developer_id or current_user.id
    now = datetime.now(timezone.utc).isoformat()

    cap = Capability(
        developer_id=dev_id,
        cap_id=req.cap_id,
        name=req.name,
        description=req.description,
        long_description=req.long_description,
        category=req.category,
        subcategory=req.subcategory,
        level=req.level,
        tags=json.dumps(req.tags),
        status="published",
        pricing_model=req.pricing_model,
        price=req.price,
        created_at=now, updated_at=now, published_at=now,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return {"id": cap.id, "cap_id": cap.cap_id, "status": "published"}


@router.put("/capabilities/{cap_id}")
def admin_update_capability(
    cap_id: str,
    req: AdminCapUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Admin update any capability"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k == "tags":
            setattr(cap, k, json.dumps(v))
        else:
            setattr(cap, k, v)
    cap.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"status": "ok", "cap_id": cap_id}


@router.delete("/capabilities/{cap_id}")
def admin_delete_capability(
    cap_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Admin delete a capability (only draft/rejected)"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")
    if cap.status == "published":
        raise HTTPException(400, "Cannot delete published capability, suspend it first")
    db.delete(cap)
    db.commit()
    return {"status": "deleted"}


# ═══════════════════════════════════════════
# 批量定价
# ═══════════════════════════════════════════

class BatchPricing(BaseModel):
    cap_ids: list[str]
    pricing_model: str | None = None
    price: float | None = None
    multiplier: float | None = None  # e.g. 1.1 = 10% increase

@router.post("/pricing/batch")
def batch_pricing(
    req: BatchPricing,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Batch update pricing"""
    updated = 0
    for cid in req.cap_ids:
        cap = db.query(Capability).filter(Capability.cap_id == cid).first()
        if not cap:
            continue
        if req.pricing_model:
            cap.pricing_model = req.pricing_model
        if req.price is not None:
            cap.price = req.price
        if req.multiplier is not None:
            cap.price = round(cap.price * req.multiplier, 2)
        cap.updated_at = datetime.now(timezone.utc).isoformat()
        updated += 1
    db.commit()
    return {"updated": updated}
