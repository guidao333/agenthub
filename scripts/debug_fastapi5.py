import sys
print("Testing fastapi.routing imports one by one...", flush=True)

# From routing.py imports
imports = [
    "import contextlib",
    "import email.message",
    "import functools",
    "import inspect",
    "import json",
    "import types",
    "from collections.abc import AsyncIterator, Awaitable, Callable",
    "from contextlib import AbstractAsyncContextManager",
    "from enum import Enum, IntEnum",
    "import anyio",
    "from annotated_doc import Doc",
]

for stmt in imports:
    print(f"  {stmt}...", flush=True)
    try:
        exec(stmt)
        print(f"    OK", flush=True)
    except Exception as e:
        print(f"    FAIL: {e}", flush=True)
        import traceback; traceback.print_exc()
        break

print("\nAll basic imports OK!", flush=True)

# These may have circular deps
sensitive = [
    "from fastapi import params",
]
for stmt in sensitive:
    print(f"  {stmt}...", flush=True)
    try:
        exec(stmt)
        print(f"    OK", flush=True)
    except Exception as e:
        print(f"    FAIL: {e}", flush=True)
        import traceback; traceback.print_exc()
        break
