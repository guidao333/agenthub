import sys, time
t0=time.time()
print("Importing fastapi 0.136.1...", flush=True)
import fastapi
print(f"OK! v{fastapi.__version__} in {time.time()-t0:.1f}s", flush=True)
from fastapi import APIRouter
print("APIRouter import OK", flush=True)
router = APIRouter()
print("APIRouter instantiate OK!", flush=True)
