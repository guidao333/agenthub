#!/usr/bin/env python3
import sys
sys.path.insert(0, "/opt/agenthub/backend")
import app
print("app modules:", [x for x in dir(app) if not x.startswith("_")])
