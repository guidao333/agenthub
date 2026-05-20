import sys, importlib, os
importlib.invalidate_caches()
print("cache cleared", flush=True)

# Check if fastapi can be imported now
try:
    import fastapi
    print(f"fastapi {fastapi.__version__} OK!", flush=True)
except Exception as e:
    print(f"FAIL: {e}", flush=True)
    import traceback
    traceback.print_exc()
