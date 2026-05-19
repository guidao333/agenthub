"""Market routes: browse, search, subscribe capabilities"""
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import get_db, Capability, Subscription, Review, User
from ..auth import get_current_user
import secrets

router = APIRouter(prefix="/market", tags=["market"])


class CapabilityListItem(BaseModel):
    id: int
    cap_id: str
    name: str
    description: str | None
    category: str | None
    subcategory: str | None
    tags: list | None
    pricing_model: str | None
    price: float
    call_count: int
    avg_rating: float
    developer_name: str | None

    class Config:
        from_attributes = True


class CapabilityDetail(CapabilityListItem):
    long_description: str | None
    version: str
    llm_mode: str
    interfaces_config: dict | None
    published_at: str | None


# ---- Public endpoints ----

@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Get full category tree with counts from config + DB stats"""
    from pathlib import Path
    import yaml as _yaml

    yaml_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "categories.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = _yaml.safe_load(f)
    else:
        cfg = {"categories": []}

    # Get counts from DB
    from sqlalchemy import func
    cap_counts = dict(
        db.query(Capability.category, func.count(Capability.id))
        .filter(Capability.status == "published")
        .group_by(Capability.category)
        .all()
    )
    subcap_counts = dict(
        db.query(Capability.subcategory, func.count(Capability.id))
        .filter(Capability.status == "published")
        .group_by(Capability.subcategory)
        .all()
    )

    result = []
    for cat in cfg.get("categories", []):
        cat_item = {
            "id": cat["id"],
            "name": cat["name"],
            "icon": cat.get("icon", "📦"),
            "description": cat.get("description", ""),
            "color": cat.get("color", "#6B7280"),
            "count": cap_counts.get(cat["id"], 0),
            "subcategories": [],
        }
        for sub in cat.get("subcategories", []):
            cat_item["subcategories"].append({
                "id": sub["id"],
                "name": sub["name"],
                "description": sub.get("description", ""),
                "count": subcap_counts.get(sub["id"], 0),
            })
        result.append(cat_item)
    return result


@router.get("/capabilities")
def list_capabilities(
    category: str | None = None,
    subcategory: str | None = None,
    level: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    sort: str = "call_count",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List published capabilities with filtering"""
    q = db.query(Capability).filter(Capability.status == "published")

    if category:
        q = q.filter(Capability.category == category)
    if subcategory:
        q = q.filter(Capability.subcategory == subcategory)
    if level:
        q = q.filter(Capability.level == level)
    if tag:
        q = q.filter(Capability.tags.contains(tag))
    if search:
        q = q.filter(or_(
            Capability.name.contains(search),
            Capability.description.contains(search),
            Capability.tags.contains(search),
        ))

    # Sort
    if sort == "call_count":
        q = q.order_by(Capability.call_count.desc())
    elif sort == "rating":
        q = q.order_by(Capability.avg_rating.desc())
    elif sort == "new":
        q = q.order_by(Capability.published_at.desc())
    else:
        q = q.order_by(Capability.call_count.desc())

    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()

    result = []
    for cap in items:
        dev = db.query(User).filter(User.id == cap.developer_id).first()
        result.append({
            "id": cap.id,
            "cap_id": cap.cap_id,
            "name": cap.name,
            "description": cap.description,
            "category": cap.category,
            "subcategory": cap.subcategory,
            "level": cap.level,
            "dependencies": json.loads(cap.dependencies) if cap.dependencies else [],
            "tags": json.loads(cap.tags) if cap.tags else [],
            "pricing_model": cap.pricing_model,
            "price": cap.price,
            "call_count": cap.call_count,
            "avg_rating": cap.avg_rating,
            "developer_name": dev.username if dev else None,
        })

    return {"total": total, "page": page, "size": size, "items": result}


@router.get("/capabilities/{cap_id}")
def get_capability(cap_id: str, db: Session = Depends(get_db)):
    """Get capability detail"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap and cap_id.isdigit():
        cap = db.query(Capability).filter(Capability.id == int(cap_id)).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    dev = db.query(User).filter(User.id == cap.developer_id).first()
    reviews = db.query(Review).filter(Review.capability_id == cap.id).order_by(Review.created_at.desc()).limit(10).all()

    return {
        "id": cap.id,
        "cap_id": cap.cap_id,
        "name": cap.name,
        "version": cap.version,
        "description": cap.description,
        "long_description": cap.long_description,
        "category": cap.category,
        "subcategory": cap.subcategory,
        "level": cap.level,
        "dependencies": json.loads(cap.dependencies) if cap.dependencies else [],
        "tags": json.loads(cap.tags) if cap.tags else [],
        "pricing_model": cap.pricing_model,
        "price": cap.price,
        "llm_mode": cap.llm_mode,
        "interfaces_config": json.loads(cap.interfaces_config) if cap.interfaces_config else None,
        "call_count": cap.call_count,
        "avg_rating": cap.avg_rating,
        "published_at": cap.published_at,
        "developer_name": dev.username if dev else None,
        "reviews": [{"rating": r.rating, "comment": r.comment, "created_at": r.created_at} for r in reviews],
    }


@router.get("/hot")
def hot_capabilities(db: Session = Depends(get_db)):
    """Top 10 hot capabilities"""
    caps = db.query(Capability).filter(Capability.status == "published"
                        ).order_by(Capability.call_count.desc()).limit(10).all()
    return [{"cap_id": c.cap_id, "name": c.name, "call_count": c.call_count, "price": c.price} for c in caps]


@router.get("/new")
def new_capabilities(db: Session = Depends(get_db)):
    """Recently published capabilities"""
    caps = db.query(Capability).filter(Capability.status == "published"
                        ).order_by(Capability.published_at.desc()).limit(10).all()
    return [{"cap_id": c.cap_id, "name": c.name, "published_at": c.published_at, "price": c.price} for c in caps]


# ---- Authenticated endpoints ----

@router.post("/capabilities/{cap_id}/subscribe")
def subscribe_capability(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe to a capability"""
    if current_user.role != "customer":
        raise HTTPException(403, "Only customers can subscribe")

    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap or cap.status != "published":
        raise HTTPException(404, "Capability not found or not available")

    # Check existing subscription
    existing = db.query(Subscription).filter(
        Subscription.customer_id == current_user.id,
        Subscription.capability_id == cap.id,
        Subscription.status == "active",
    ).first()
    if existing:
        raise HTTPException(400, "Already subscribed")

    now = datetime.now(timezone.utc).isoformat()
    sub = Subscription(
        customer_id=current_user.id,
        capability_id=cap.id,
        api_key=f"ahk_{secrets.token_hex(24)}",
        started_at=now,
    )
    db.add(sub)
    cap.download_count += 1
    db.commit()
    db.refresh(sub)

    return {"subscription_id": sub.id, "api_key": sub.api_key, "capability": cap.name}


@router.post("/capabilities/{cap_id}/review")
def submit_review(
    cap_id: str,
    rating: int,
    comment: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a review for a capability"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    if not 1 <= rating <= 5:
        raise HTTPException(400, "Rating must be 1-5")

    now = datetime.now(timezone.utc).isoformat()
    review = Review(
        user_id=current_user.id,
        capability_id=cap.id,
        rating=rating,
        comment=comment,
        created_at=now,
    )
    db.add(review)

    # Update average rating
    all_reviews = db.query(Review).filter(Review.capability_id == cap.id).all()
    avg = sum(r.rating for r in all_reviews) / len(all_reviews)
    cap.avg_rating = round(avg, 1)

    db.commit()
    return {"status": "ok"}
