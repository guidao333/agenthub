import sys
print("Testing fastapi import...", flush=True)
try:
    import fastapi
    print(f"fastapi imported: {fastapi.__version__}", flush=True)
    print(f"fastapi file: {fastapi.__file__}", flush=True)
except Exception as e:
    print(f"FAIL: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("Testing starlette import...", flush=True)
import starlette
print(f"starlette: {starlette.__version__}", flush=True)
print(f"starlette file: {starlette.__file__}", flush=True)

print("Testing starlette.applications import...", flush=True)
from starlette.applications import Starlette
print("OK", flush=True)

print("Testing fastapi import again...", flush=True)
import fastapi
print("OK!", flush=True)
