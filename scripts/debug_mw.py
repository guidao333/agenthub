#!/usr/bin/env python3
import sys, os, time, traceback
sys.path.insert(0, "/opt/agenthub/backend")

print("Test middleware individually:", flush=True)

for mod in ["app.middleware.error_handler", "app.middleware.request_log", "app.middleware.rate_limit"]:
    print(f"\nImporting {mod}...", flush=True)
    try:
        t0 = time.time()
        exec(f"import {mod}")
        print(f"  OK ({time.time()-t0:.2f}s)", flush=True)
    except Exception as e:
        print(f"  FAIL: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

print("\n\nAll middleware OK!", flush=True)
