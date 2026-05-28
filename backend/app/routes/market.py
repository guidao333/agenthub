"""Market routes: browse, search, subscribe capabilities"""
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import get_db, Capability, Subscription, Review, User
from ..auth import get_current_user
from ..config import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
import secrets

router = APIRouter(prefix="/market", tags=["market"])


def get_optional_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User | None:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None
    return db.query(User).filter(User.username == username, User.status == "active").first()


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
    """Get full category tree from database"""
    from ..models import Category
    from sqlalchemy import func

    parents = db.query(Category).filter(Category.parent_id == 0).order_by(Category.sort_order).all()
    
    cap_counts = dict(
        db.query(Capability.category, func.count(Capability.id))
        .filter(Capability.status == "published")
        .group_by(Capability.category).all()
    )
    sub_counts = dict(
        db.query(Capability.subcategory, func.count(Capability.id))
        .filter(Capability.status == "published")
        .group_by(Capability.subcategory).all()
    )

    result = []
    for p in parents:
        subs = db.query(Category).filter(Category.parent_id == p.id).order_by(Category.sort_order).all()
        sub_list = [{
            "id": s.cat_id, "name": s.name, "description": s.description,
            "count": sub_counts.get(s.cat_id, 0),
        } for s in subs]
        result.append({
            "id": p.cat_id, "name": p.name, "icon": p.icon,
            "color": p.color, "description": p.description,
            "count": cap_counts.get(p.cat_id, 0), "subcategories": sub_list,
        })
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
def get_capability(
    cap_id: str,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get capability detail"""
    cap = db.query(Capability).filter(Capability.cap_id == cap_id).first()
    if not cap and cap_id.isdigit():
        cap = db.query(Capability).filter(Capability.id == int(cap_id)).first()
    if not cap:
        raise HTTPException(404, "Capability not found")

    dev = db.query(User).filter(User.id == cap.developer_id).first()
    reviews = db.query(Review).filter(Review.capability_id == cap.id).order_by(Review.created_at.desc()).limit(10).all()
    active_subscription = None
    if current_user:
        active_subscription = db.query(Subscription).filter(
            Subscription.customer_id == current_user.id,
            Subscription.capability_id == cap.id,
            Subscription.status == "active",
        ).first()

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
        "is_subscribed": bool(active_subscription),
        "subscription_id": active_subscription.id if active_subscription else None,
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
    if current_user.role not in ("customer", "admin"):
        raise HTTPException(403, "Only customers and admins can subscribe")

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
    cap.download_count = (cap.download_count or 0) + 1
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
