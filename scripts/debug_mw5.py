import sys, os
sys.path.insert(0, "/opt/agenthub/backend")

print("Testing fastapi imports from error_handler...", flush=True)
print("1. fastapi Request...", flush=True)
from fastapi import Request
print("2. fastapi JSONResponse...", flush=True)
from fastapi.responses import JSONResponse
print("3. logging.getLogger...", flush=True)
import logging
logging.getLogger("agenthub.error")
print("ALL OK!", flush=True)
