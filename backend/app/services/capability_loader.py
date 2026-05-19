"""能力包加载器 - 解析 capability.yaml 并加载工具脚本"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Optional
from ..config import CAPABILITIES_DIR

logger = logging.getLogger("agenthub.cap_loader")


def load_capability(cap_id: str) -> Optional[dict]:
    """
    加载能力包，返回解析后的配置

    Returns:
        {
            "yaml": {...},          # capability.yaml 内容
            "tools": [...],         # tools/*.py 文件路径列表
            "adapters": [...],      # adapters/*.py 文件路径列表
            "knowledge": [...],     # knowledge/*.md 文件路径列表
            "soul": "...",          # SOUL.md 内容
            "readme": "...",        # README.md 内容
            "test_cases": [...]     # tests/ 下的测试文件
        }
    """
    cap_dir = CAPABILITIES_DIR / cap_id
    if not cap_dir.exists():
        logger.warning(f"Capability directory not found: {cap_dir}")
        return None

    result = {"yaml": {}, "tools": [], "adapters": [], "knowledge": [], "soul": "", "readme": ""}

    # 加载 capability.yaml
    yaml_path = cap_dir / "capability.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            result["yaml"] = yaml.safe_load(f)

    # 加载 agent/SOUL.md
    soul_path = cap_dir / "agent" / "SOUL.md"
    if soul_path.exists():
        with open(soul_path, "r", encoding="utf-8") as f:
            result["soul"] = f.read()

    # 加载 tools/
    tools_dir = cap_dir / "agent" / "tools"
    if tools_dir.exists():
        for f in sorted(tools_dir.glob("*.py")):
            result["tools"].append(str(f))

    # 加载 adapters/
    adapters_dir = cap_dir / "adapters"
    if adapters_dir.exists():
        for f in sorted(adapters_dir.glob("*.py")):
            result["adapters"].append(str(f))

    # 加载 knowledge/
    knowledge_dir = cap_dir / "agent" / "knowledge"
    if knowledge_dir.exists():
        for f in sorted(knowledge_dir.glob("*.md")):
            with open(f, "r", encoding="utf-8") as fh:
                result["knowledge"].append({"file": f.name, "content": fh.read()})

    # 加载 README.md
    readme_path = cap_dir / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            result["readme"] = f.read()

    # 加载 tests/
    tests_dir = cap_dir / "tests"
    if tests_dir.exists():
        result["test_cases"] = [str(f) for f in sorted(tests_dir.glob("*.py"))]

    return result


def get_tool_script_path(cap_id: str, tool_name: str) -> Optional[str]:
    """获取指定工具脚本的路径"""
    cap = load_capability(cap_id)
    if not cap:
        return None
    for tool_path in cap.get("tools", []):
        if Path(tool_path).stem == tool_name:
            return tool_path
    return None


def get_capability_yaml(cap_id: str) -> Optional[dict]:
    """快速获取 capability.yaml 内容"""
    yaml_path = CAPABILITIES_DIR / cap_id / "capability.yaml"
    if not yaml_path.exists():
        return None
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
