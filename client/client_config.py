"""Local configuration storage for AgentHub client."""

import json
import os
import platform
from pathlib import Path


def config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return root / "AgentHub" / "Client"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "AgentHub" / "Client"
    return Path.home() / ".config" / "agenthub" / "client"


CONFIG_FILE = config_dir() / "config.json"
BACKUP_FILE = config_dir() / "config.json.bak"
INSTALL_BACKUP_FILE = config_dir() / "config.json.installbak"


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _merge_config(base: dict, extra: dict) -> dict:
    merged = dict(base or {})
    if not isinstance(extra, dict):
        return merged
    for key, value in extra.items():
        if key == "capability_configs" and isinstance(value, dict):
            current = merged.get(key) if isinstance(merged.get(key), dict) else {}
            current.update({cap_id: cfg for cap_id, cfg in value.items() if isinstance(cfg, dict)})
            merged[key] = current
        elif key == "capability_api_keys" and isinstance(value, dict):
            current = merged.get(key) if isinstance(merged.get(key), dict) else {}
            current.update({cap_id: api_key for cap_id, api_key in value.items() if api_key})
            merged[key] = current
        elif value and not merged.get(key):
            merged[key] = value
    return merged


def load_config() -> dict:
    config = {}
    for path in (INSTALL_BACKUP_FILE, BACKUP_FILE, CONFIG_FILE):
        config = _merge_config(config, _read_json(path))
    if not config:
        return {}
    if not config.get("api_key"):
        keys = config.get("capability_api_keys")
        if isinstance(keys, dict):
            config["api_key"] = next((value for value in keys.values() if value), "")
    return config


def repair_config() -> dict:
    config = load_config()
    if config:
        save_config(config)
    return config


def save_config(config: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            BACKUP_FILE.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
    tmp_file = CONFIG_FILE.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_file.replace(CONFIG_FILE)


def update_config(values: dict) -> dict:
    config = load_config()
    config.update(values or {})
    save_config(config)
    return config


def load_capability_configs() -> dict:
    config = load_config()
    configs = config.get("capability_configs")
    return configs if isinstance(configs, dict) else {}


def save_capability_config(cap_id: str, capability_config: dict) -> dict:
    config = load_config()
    configs = config.get("capability_configs")
    if not isinstance(configs, dict):
        configs = {}
    configs[cap_id] = capability_config or {}
    config["capability_configs"] = configs
    save_config(config)
    return configs[cap_id]


def load_capability_api_keys() -> dict:
    config = load_config()
    keys = config.get("capability_api_keys")
    return keys if isinstance(keys, dict) else {}


def save_capability_api_key(cap_id: str, api_key: str) -> dict:
    config = load_config()
    keys = config.get("capability_api_keys")
    if not isinstance(keys, dict):
        keys = {}
    keys[cap_id] = (api_key or "").strip()
    keys = {key: value for key, value in keys.items() if value}
    config["capability_api_keys"] = keys
    if api_key and not config.get("api_key"):
        config["api_key"] = api_key.strip()
    save_config(config)
    return keys
