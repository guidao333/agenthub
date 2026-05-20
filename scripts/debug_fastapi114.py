import sys, time
t0=time.time()
print("Importing fastapi 0.114.2...", flush=True)
import fastapi
print(f"OK! v{fastapi.__version__} in {time.time()-t0:.1f}s", flush=True)
from fastapi import APIRouter
router = APIRouter()
print(f"APIRouter OK!", flush=True)
