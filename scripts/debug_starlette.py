import sys, time
print("1. starlette.routing...", flush=True)
t0=time.time()
from starlette import routing
print(f"   OK ({time.time()-t0:.2f}s)", flush=True)

print("2. starlette.applications...", flush=True)
t0=time.time()
from starlette.applications import Starlette
print(f"   OK ({time.time()-t0:.2f}s)", flush=True)

print("3. starlette.requests...", flush=True)
t0=time.time()
from starlette.requests import Request
print(f"   OK ({time.time()-t0:.2f}s)", flush=True)

print("4. starlette.responses...", flush=True)
t0=time.time()
from starlette.responses import JSONResponse
print(f"   OK ({time.time()-t0:.2f}s)", flush=True)

print("ALL STARLETTE OK!", flush=True)
