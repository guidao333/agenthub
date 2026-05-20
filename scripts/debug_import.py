#!/usr/bin/env python3
import sys, os, time
sys.path.insert(0, "/opt/agenthub/backend")

print("Step 1: config...", flush=True)
import app.config
print(f"  DATA_DIR={app.config.DATA_DIR}", flush=True)

print("Step 2: models...", flush=True)
import app.models
print(f"  DB URL: {app.models.engine.url}", flush=True)

print("Step 3: utils...", flush=True)
import app.utils.errors
import app.utils.helpers
import app.utils.crypto
print("  utils OK", flush=True)

print("Step 4: services...", flush=True)
import app.services
print("  services OK", flush=True)

print("Step 5: middleware...", flush=True)
import app.middleware.error_handler
import app.middleware.request_log
import app.middleware.rate_limit
print("  middleware OK", flush=True)

print("Step 6: routes...", flush=True)
import app.routes
print("  routes OK", flush=True)

print("Step 7: main...", flush=True)
import app.main
print(f"  app type: {type(app.main.app).__name__}", flush=True)
print(f"  routes: {len(app.main.app.routes)}", flush=True)

print("\nALL OK!", flush=True)
