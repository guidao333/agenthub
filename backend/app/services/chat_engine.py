"""Chat engine: LLM interaction with function calling"""
import json
import os
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import AsyncGenerator
import httpx
from ..config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    CAPABILITIES_DIR, MAX_TOOL_CALL_ROUNDS, CAPABILITY_TIMEOUT_SECONDS,
)

# Output filter patterns - block internal logic disclosure
BLOCKED_PATTERNS = [
    "知识库", "SOUL.md", "系统提示", "system prompt",
    "内部实现", "代码逻辑", "capability.yaml",
    "我已经被指示", "我被要求不",
]


class ChatEngine:
    """Handles LLM chat with function calling for a capability"""

    def __init__(self, capability):
        self.capability = capability
        self.soul_md = ""
        self.tools = []
        self.tool_scripts = {}
        self._load_capability()

    def _load_capability(self):
        """Load capability SOUL.md and tool definitions"""
        cap_dir = CAPABILITIES_DIR / self.capability.cap_id
        if not cap_dir.exists():
            return

        # Load SOUL.md
        soul_path = cap_dir / "agent" / "SOUL.md"
        if soul_path.exists():
            self.soul_md = soul_path.read_text(encoding="utf-8")

        # Load capability.yaml for tool definitions
        yaml_path = cap_dir / "capability.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                # Extract API params as tools if configured
                interfaces = config.get("interfaces", {})
                if interfaces.get("api_params"):
                    self.tools = [{
                        "type": "function",
                        "function": {
                            "name": "execute_capability",
                            "description": f"Execute {self.capability.name}",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    p["name"]: {"type": p["type"], "description": p.get("description", "")}
                                    for p in interfaces["api_params"]
                                },
                                "required": [p["name"] for p in interfaces["api_params"] if p.get("required")],
                            },
                        },
                    }]

        # Load tool scripts
        tools_dir = cap_dir / "agent" / "tools"
        if tools_dir.exists():
            for script in tools_dir.glob("*.py"):
                self.tool_scripts[script.stem] = str(script)

    def _build_messages(self, history: list) -> list:
        """Build messages array for LLM API"""
        messages = []
        if self.soul_md:
            messages.append({"role": "system", "content": self.soul_md})
        else:
            messages.append({
                "role": "system",
                "content": f"你是 {self.capability.name} 的AI助手。{self.capability.description or ''}"
            })
        messages.extend(history)
        return messages

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool script in a subprocess"""
        script_path = self.tool_scripts.get(tool_name)
        if not script_path:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})

        # Write arguments to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(arguments, f)
            args_file = f.name

        try:
            result = subprocess.run(
                ["python3", script_path, args_file],
                capture_output=True, text=True, timeout=CAPABILITY_TIMEOUT_SECONDS,
                env={**os.environ, "AGENTHUB_CAP_ID": self.capability.cap_id},
            )
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "Tool execution timed out"})
        finally:
            os.unlink(args_file)

    def _filter_output(self, text: str) -> str:
        """Filter sensitive information from output"""
        for pattern in BLOCKED_PATTERNS:
            if pattern in text:
                # Replace the sensitive part
                text = text.replace(pattern, "***")
        return text

    async def stream_chat(self, history: list) -> AsyncGenerator[str, None]:
        """Stream chat response with tool calling loop"""
        messages = self._build_messages(history)

        async with httpx.AsyncClient(timeout=60.0) as client:
            for round_num in range(MAX_TOOL_CALL_ROUNDS + 1):
                # Call LLM API
                payload = {
                    "model": DEEPSEEK_MODEL,
                    "messages": messages,
                    "stream": True,
                }
                if self.tools:
                    payload["tools"] = self.tools

                headers = {
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                }

                full_content = ""
                tool_calls = []

                async with client.stream(
                    "POST",
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as resp:
                    if resp.status_code != 200:
                        error_text = await resp.aread()
                        yield f"[Error: LLM API returned {resp.status_code}]"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})

                            # Content
                            if delta.get("content"):
                                content = self._filter_output(delta["content"])
                                full_content += content
                                yield content

                            # Tool calls
                            if delta.get("tool_calls"):
                                for tc in delta["tool_calls"]:
                                    if tc.get("index") is not None:
                                        while len(tool_calls) <= tc["index"]:
                                            tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                                        idx = tc["index"]
                                        if tc.get("id"):
                                            tool_calls[idx]["id"] = tc["id"]
                                        if tc.get("function", {}).get("name"):
                                            tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                                        if tc.get("function", {}).get("arguments"):
                                            tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                        except json.JSONDecodeError:
                            continue

                # If no tool calls, we're done
                if not tool_calls:
                    return

                # Process tool calls
                yield json.dumps({"type": "tool_call", "count": len(tool_calls)})

                messages.append({
                    "role": "assistant",
                    "content": full_content or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = self._execute_tool(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result[:4000],  # Limit tool output
                    })

        # Exhausted tool call rounds
        return
