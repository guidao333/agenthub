import sys, time
t0 = time.time()
print("Importing fastapi (0.115.6)...", flush=True)
import fastapi
print(f"OK! version={fastapi.__version__} time={time.time()-t0:.1f}s", flush=True)
