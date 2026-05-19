"""Category & taxonomy configuration routes"""
import os
import yaml
from fastapi import APIRouter
from pathlib import Path

router = APIRouter(prefix="/config", tags=["config"])

# Load categories.yaml
_config_dir = Path(__file__).resolve().parent.parent.parent.parent / "config"
_categories_cache = None


def _load_categories():
    global _categories_cache
    if _categories_cache:
        return _categories_cache
    yaml_path = _config_dir / "categories.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            _categories_cache = yaml.safe_load(f)
    else:
        _categories_cache = {"categories": [], "tag_dimensions": [], "capability_levels": {}}
    return _categories_cache


def reload_categories():
    """Force reload categories from disk"""
    global _categories_cache
    _categories_cache = None
    return _load_categories()


@router.get("/categories")
def get_categories():
    """Get full category tree with metadata"""
    data = _load_categories()
    return {
        "categories": data.get("categories", []),
        "tag_dimensions": data.get("tag_dimensions", []),
        "capability_levels": data.get("capability_levels", {}),
    }


@router.get("/categories/tree")
def get_category_tree():
    """Get simplified category tree for navigation"""
    data = _load_categories()
    tree = []
    for cat in data.get("categories", []):
        tree.append({
            "id": cat["id"],
            "name": cat["name"],
            "icon": cat.get("icon", "📦"),
            "description": cat.get("description", ""),
            "color": cat.get("color", "#6B7280"),
            "subcategories": [
                {
                    "id": sub["id"],
                    "name": sub["name"],
                    "description": sub.get("description", ""),
                }
                for sub in cat.get("subcategories", [])
            ],
        })
    return tree


@router.get("/categories/flat")
def get_categories_flat():
    """Get flat list of all categories and subcategories"""
    data = _load_categories()
    flat = []
    for cat in data.get("categories", []):
        flat.append({
            "id": cat["id"],
            "name": cat["name"],
            "icon": cat.get("icon", "📦"),
            "is_parent": True,
        })
        for sub in cat.get("subcategories", []):
            flat.append({
                "id": sub["id"],
                "name": sub["name"],
                "parent_id": cat["id"],
                "is_parent": False,
            })
    return flat


@router.get("/tags")
def get_tag_dimensions():
    """Get all tag dimensions for filtering"""
    data = _load_categories()
    return data.get("tag_dimensions", [])


@router.get("/levels")
def get_capability_levels():
    """Get capability level definitions"""
    data = _load_categories()
    return data.get("capability_levels", {})
