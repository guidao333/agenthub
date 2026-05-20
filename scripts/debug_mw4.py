import sys, os
sys.path.insert(0, "/opt/agenthub/backend")

print("Testing imports from inside the file directly...", flush=True)
print("1. importing logging...", flush=True)
import logging
print("2. importing traceback...", flush=True)
import traceback
print("3. importing from app.utils.errors...", flush=True)
from app.utils.errors import AppException, ErrorCode, api_response
print("   AppException OK", flush=True)

print("4. importing error_handler directly (file exec simulation)...", flush=True)
# Read and exec the file content manually
with open("/opt/agenthub/backend/app/middleware/error_handler.py") as f:
    code = compile(f.read(), "error_handler.py", "exec")
exec(code)
print("   error_handler OK", flush=True)
