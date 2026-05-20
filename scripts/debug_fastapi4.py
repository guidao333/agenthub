import sys
print("Testing annotated_doc...", flush=True)
from annotated_doc import Doc
print("annotated_doc OK", flush=True)

print("fastapi.routing...", flush=True)
from fastapi import routing
print("routing OK", flush=True)

print("fastapi.datastructures...", flush=True)
from fastapi.datastructures import Default, DefaultPlaceholder
print("datastructures OK", flush=True)

print("fastapi.applications...", flush=True)
from fastapi.applications import FastAPI
print("FastAPI OK!", flush=True)
