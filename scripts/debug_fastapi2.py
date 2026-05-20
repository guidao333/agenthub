import sys, os
# FastAPI's __init__.py line by line

print("1. import starlette.status", flush=True)
from starlette import status

print("2. import dataclasses", flush=True)
import dataclasses

print("3. import typing", flush=True)
import typing

print("4. import fastapi.applications", flush=True)
from fastapi.applications import FastAPI

print("ALL OK!", flush=True)
