import sys
checks = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("sqlalchemy", "sqlalchemy"),
    ("openai", "openai"),
    ("jose", "python-jose"),
    ("yaml", "pyyaml"),
    ("httpx", "httpx"),
]
ok = True
for mod_name, pkg_name in checks:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "OK")
        print(f"  [OK] {pkg_name} {ver}")
    except ImportError as e:
        print(f"  [FAIL] {pkg_name}: {e}")
        ok = False
sys.exit(0 if ok else 1)
