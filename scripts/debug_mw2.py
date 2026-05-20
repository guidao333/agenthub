#!/usr/bin/env python3
import sys, os
sys.path.insert(0, "/opt/agenthub/backend")

# Test direct imports one by one
tests = [
    "from app.middleware import error_handler",
    "from app.middleware import rate_limit",
    "from app.middleware import request_log",
]

for stmt in tests:
    print(f"Trying: {stmt}", flush=True)
    try:
        exec(stmt)
        print("  OK", flush=True)
    except Exception as e:
        print(f"  FAIL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        break
