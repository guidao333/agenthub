import sys
sys.path.insert(0, ".")
try:
    from app.main import app
    print(f"Import OK: {type(app).__name__}")
    print(f"Routes loaded: {len(app.routes)}")
    # Print all routes
    for r in app.routes:
        if hasattr(r, "methods") and hasattr(r, "path"):
            print(f"  {','.join(r.methods)} {r.path}")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
