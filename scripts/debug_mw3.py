import sys, importlib.util, os
sys.path.insert(0, "/opt/agenthub/backend")

# Load error_handler directly by file path
spec = importlib.util.spec_from_file_location(
    "error_handler",
    "/opt/agenthub/backend/app/middleware/error_handler.py",
    submodule_search_locations=[]
)
if spec is None:
    print("FAIL: spec is None - file not found or invalid", flush=True)
    sys.exit(1)

print("Found error_handler.py spec, loading...", flush=True)
mod = importlib.util.module_from_spec(spec)
print("Module created, executing...", flush=True)
spec.loader.exec_module(mod)
print("OK!", flush=True)
