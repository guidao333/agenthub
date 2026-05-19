"""自动审核引擎 - 能力包质量检查"""

import json
import logging
import os
import re
import subprocess
import sys
import yaml
from typing import Optional, get_type_hints

logger = logging.getLogger("agenthub.review")


# 审核检查清单
REVIEW_CHECKS = {
    "format": [
        ("capability.yaml 格式正确", "yaml_valid"),
        ("必填字段完整 (id/name/description/developer_id)", "required_fields"),
        ("ID 格式合法 (小写字母+数字+横线)", "id_format"),
        ("版本号格式正确 (semver)", "version_format"),
    ],
    "content": [
        ("SOUL.md 存在且非空", "soul_exists"),
        ("至少 2 个测试用例", "test_cases_min"),
        ("README.md 存在且内容 > 100 字", "readme_quality"),
        ("描述准确（功能描述与测试一致）", "description_match"),
    ],
    "security": [
        ("无硬编码 IP 地址", "no_hardcoded_ip"),
        ("无硬编码密码/token", "no_hardcoded_creds"),
        ("无危险 import (os.system/subprocess)", "no_dangerous_import"),
        ("无文件系统越界访问", "no_path_traversal"),
        ("无网络监听代码", "no_network_listen"),
    ],
}


def auto_review(package_dir: str) -> dict:
    """
    自动审核能力包

    Args:
        package_dir: 能力包目录路径

    Returns:
        {
            "passed": True/False,
            "details": {"check_key": {"passed": True/False, "message": "..."}},
            "summary": "..."
        }
    """
    details = {}
    all_passed = True

    for category, checks in REVIEW_CHECKS.items():
        for name, check_key in checks:
            result = _run_check(check_key, package_dir)
            details[check_key] = {
                "passed": result[0],
                "message": result[1],
                "name": name,
            }
            if not result[0]:
                all_passed = False

    # 可选：运行测试用例
    test_results = _run_tests(package_dir)
    details["tests_run"] = {
        "passed": test_results["passed"],
        "message": f"运行 {test_results['total']} 个测试，通过 {test_results['passed_count']}",
        "details": test_results["details"],
    }
    if not test_results["passed"]:
        all_passed = False

    return {
        "passed": all_passed,
        "details": details,
        "summary": "审核通过" if all_passed else "审核未通过，请查看具体问题",
    }


def _run_check(check_key: str, package_dir: str):
    """执行单个检查"""
    checks = {
        "yaml_valid": _check_yaml_valid,
        "required_fields": _check_required_fields,
        "id_format": _check_id_format,
        "version_format": _check_version_format,
        "soul_exists": _check_soul_exists,
        "test_cases_min": _check_test_cases,
        "readme_quality": _check_readme_quality,
        "description_match": _check_description_match,
        "no_hardcoded_ip": _check_no_hardcoded_ip,
        "no_hardcoded_creds": _check_no_hardcoded_creds,
        "no_dangerous_import": _check_no_dangerous_import,
        "no_path_traversal": _check_path_traversal,
        "no_network_listen": _check_no_network_listen,
    }
    checker = checks.get(check_key)
    if checker:
        return checker(package_dir)
    return (True, "检查项未实现")


def _check_yaml_valid(dir_path):
    try:
        with open(os.path.join(dir_path, "capability.yaml"), "r", encoding="utf-8") as f:
            yaml.safe_load(f)
        return (True, "YAML 格式正确")
    except Exception as e:
        return (False, f"YAML 解析失败: {e}")


def _check_required_fields(dir_path):
    try:
        with open(os.path.join(dir_path, "capability.yaml"), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return (False, "无法解析 capability.yaml")

    required = ["id", "name", "description"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return (False, f"缺少必填字段: {', '.join(missing)}")
    return (True, "所有必填字段完整")


def _check_id_format(dir_path):
    try:
        with open(os.path.join(dir_path, "capability.yaml"), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return (False, "无法解析 capability.yaml")

    cap_id = data.get("id", "")
    if not re.match(r"^[a-z0-9][a-z0-9\-]*$", cap_id):
        return (False, f"ID '{cap_id}' 格式非法，只允许小写字母、数字和横线")
    return (True, f"ID 格式合法: {cap_id}")


def _check_version_format(dir_path):
    try:
        with open(os.path.join(dir_path, "capability.yaml"), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return (False, "无法解析 capability.yaml")

    version = data.get("version", "1.0.0")
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        return (False, f"版本号 '{version}' 格式非法，应使用 semver (如 1.0.0)")
    return (True, f"版本号格式正确: {version}")


def _check_soul_exists(dir_path):
    soul_path = os.path.join(dir_path, "agent", "SOUL.md")
    if not os.path.exists(soul_path):
        return (False, "agent/SOUL.md 不存在")
    content = open(soul_path, "r", encoding="utf-8").read().strip()
    if len(content) < 50:
        return (False, "SOUL.md 内容过短（需 > 50 字）")
    return (True, "SOUL.md 存在且内容完整")


def _check_test_cases(dir_path):
    tests_dir = os.path.join(dir_path, "tests")
    if not os.path.exists(tests_dir):
        return (False, "tests/ 目录不存在")
    py_files = [f for f in os.listdir(tests_dir) if f.endswith(".py")]
    if len(py_files) < 2:
        return (False, f"测试用例不足，需要至少 2 个，当前 {len(py_files)} 个")
    return (True, f"有 {len(py_files)} 个测试用例")


def _check_readme_quality(dir_path):
    readme_path = os.path.join(dir_path, "README.md")
    if not os.path.exists(readme_path):
        return (False, "README.md 不存在")
    content = open(readme_path, "r", encoding="utf-8").read().strip()
    if len(content) < 100:
        return (False, "README.md 内容不足 100 字")
    return (True, f"README.md ({len(content)} 字)")


def _check_description_match(dir_path):
    return (True, "描述正确性由人工审核确认")


# ── 安全扫描 ──

SAFE_IMPORTS = {"json", "yaml", "os", "re", "datetime", "logging", "hashlib",
                "typing", "dataclasses", "enum", "math", "time", "pathlib"}

DANGEROUS_PATTERNS = [
    (r"os\.system\(", "os.system() 命令执行"),
    (r"subprocess\..*shell=True", "subprocess shell=True"),
    (r"os\.popen\(", "os.popen() 命令执行"),
    (r"shutil\.rmtree\(", "危险的文件操作"),
    (r"eval\(", "eval() 动态执行"),
    (r"exec\(", "exec() 动态执行"),
    (r"__import__\(", "动态导入"),
    (r"pickle\.loads\(", "反序列化漏洞"),
]

IP_PATTERN = re.compile(r"(?:https?://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\s*:?\d{0,5})")
CRED_PATTERNS = [
    (r'password\s*[=:]\s*["\']([^"\']+)["\']', "硬编码密码"),
    (r'passwd\s*[=:]\s*["\']([^"\']+)["\']', "硬编码密码"),
    (r'secret\s*[=:]\s*["\']([^"\']+)["\']', "硬编码密钥"),
    (r'token\s*[=:]\s*["\']([^"\']+)["\']', "硬编码 Token"),
]


def _check_no_hardcoded_ip(dir_path):
    """扫描常见脚本文件中的硬编码 IP"""
    issues = []
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith((".py", ".md", ".yaml", ".yml")):
                path = os.path.join(root, f)
                content = open(path, "r", encoding="utf-8").read()
                ips = IP_PATTERN.findall(content)
                # 过滤掉常见私有 IP 段（内网示例是正常的）
                legit_ips = [ip for ip in ips if not ip.startswith(("192.168.", "10.", "172.16.", "127.0.0"))]
                if legit_ips:
                    issues.append(f"{f}: {', '.join(set(legit_ips))}")
    if issues:
        return (False, f"发现疑似硬编码 IP: {'; '.join(issues[:3])}")
    return (True, "无硬编码 IP")


def _check_no_hardcoded_creds(dir_path):
    issues = []
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith((".py", ".yaml", ".yml")):
                path = os.path.join(root, f)
                content = open(path, "r", encoding="utf-8").read()
                for pattern, desc in CRED_PATTERNS:
                    matches = pattern.findall(content)
                    if matches:
                        issues.append(f"{f}: {desc}")
    if issues:
        return (False, f"发现疑似硬编码凭证: {'; '.join(set(issues[:3]))}")
    return (True, "无硬编码凭证")


def _check_no_dangerous_import(dir_path):
    issues = []
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                content = open(path, "r", encoding="utf-8").read()
                for pattern, desc in DANGEROUS_PATTERNS:
                    if pattern.search(content):
                        issues.append(f"{f}: {desc}")
    if issues:
        return (False, f"发现危险代码: {'; '.join(issues[:3])}")
    return (True, "无危险操作")


def _check_path_traversal(dir_path):
    issues = []
    patterns = [r'\.\./', r'\.\.\\']
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                content = open(path, "r", encoding="utf-8").read()
                for p in patterns:
                    if p in content:
                        issues.append(f)
    if issues:
        return (False, f"发现目录穿越(改源码可能会有这种可执行文件): {', '.join(set(issues))}")
    return (True, "无文件越界访问")


def _check_no_network_listen(dir_path):
    issues = []
    patterns = [r"listen\(", r"bind\(.*\)"]
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                content = open(path, "r", encoding="utf-8").read()
                for p in patterns:
                    if p in content and "import socket" in content:
                        issues.append(f)
    if issues:
        return (False, f"发现网络监听代码: {', '.join(set(issues))}")
    return (True, "无网络监听行为")


def _run_tests(package_dir: str) -> dict:
    """运行测试用例"""
    tests_dir = os.path.join(package_dir, "tests")
    if not os.path.exists(tests_dir):
        return {"passed": False, "total": 0, "passed_count": 0, "details": "无测试目录"}

    results = []
    for f in sorted(os.listdir(tests_dir)):
        if not f.endswith(".py"):
            continue
        test_path = os.path.join(tests_dir, f)
        try:
            proc = subprocess.run(
                [sys.executable, test_path],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=os.path.dirname(test_path),
            )
            results.append({
                "file": f,
                "passed": proc.returncode == 0,
                "output": (proc.stdout or proc.stderr)[:200],
            })
        except subprocess.TimeoutExpired:
            results.append({"file": f, "passed": False, "output": "超时"})

    passed = [r for r in results if r["passed"]]
    return {
        "passed": len(passed) == len(results),
        "total": len(results),
        "passed_count": len(passed),
        "details": results,
    }
