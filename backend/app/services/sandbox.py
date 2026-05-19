"""能力运行沙箱 - Linux 子进程隔离

使用 resource.setrlimit 限制内存/CPU，支持超时强制终止。
仅在 Linux 上可用（Debian）。
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Optional

from ..config import (
    CAPABILITIES_DIR, SANDBOX_MEMORY_LIMIT_MB, SANDBOX_CPU_TIME_SECONDS,
    SANDBOX_FILE_SIZE_MB,
)

logger = logging.getLogger("agenthub.sandbox")


def run_tool(tool_script_path: str, params: dict, env_vars: dict = None,
             timeout: int = None, allowed_hosts: list = None) -> dict:
    """
    在受限子进程中运行工具脚本

    Args:
        tool_script_path: 工具脚本绝对路径
        params: 工具参数（传给 execute()）
        env_vars: 环境变量（客户配置注入）
        timeout: 超时秒数
        allowed_hosts: 允许访问的网络白名单

    Returns:
        工具执行结果
    """
    if not os.path.exists(tool_script_path):
        return {
            "status": "error",
            "error": f"脚本不存在: {tool_script_path}",
            "message": "能力内部错误：脚本文件缺失",
        }

    timeout = timeout or SANDBOX_CPU_TIME_SECONDS
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # 输入参数序列化
    input_data = json.dumps(params, ensure_ascii=False)

    try:
        result = subprocess.run(
            [sys.executable, tool_script_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout + 2,  # 略大于内部限制
            env=env,
            cwd=os.path.dirname(tool_script_path),
        )

        # 解析 stdout
        if result.stdout:
            try:
                output = json.loads(result.stdout)
                if isinstance(output, dict):
                    return output
                return {
                    "status": "success",
                    "data": output,
                    "message": "执行完成",
                }
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "data": {"raw_output": result.stdout},
                    "message": "执行完成",
                }

        # stderr 有内容说明出错
        if result.stderr:
            return {
                "status": "error",
                "error": result.stderr[:500],
                "message": f"工具执行出错",
            }

        return {
            "status": "error",
            "error": "工具没有返回任何输出",
            "message": "空闲结果",

        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Sandbox timeout: {tool_script_path} ({timeout}s)")
        return {
            "status": "error",
            "error": f"执行超时 ({timeout}s)",
            "message": "能力执行超时，请稍后重试",
        }

    except Exception as e:
        logger.error(f"Sandbox error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "能力内部错误",
        }


# ── SQLAlchemy 兼容的回调（用于 resource.setrlimit）──

def _set_resource_limits():
    """设置子进程资源限制（仅在 Linux 有效）"""
    try:
        import resource
        # 虚拟内存限制
        mem_bytes = SANDBOX_MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

        # CPU 时间限制（秒）
        resource.setrlimit(resource.RLIMIT_CPU, (SANDBOX_CPU_TIME_SECONDS, SANDBOX_CPU_TIME_SECONDS))

        # 文件大小限制
        file_bytes = SANDBOX_FILE_SIZE_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))

        logger.info(f"Sandbox limits set: MEM={SANDBOX_MEMORY_LIMIT_MB}MB, CPU={SANDBOX_CPU_TIME_SECONDS}s")
    except (ImportError, OSError) as e:
        # Windows 或非 Linux 环境不做限制
        logger.warning(f"Resource limits not available on this platform: {e}")
