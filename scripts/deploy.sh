#!/bin/bash
# Deploy/update AgentHub from local git repo
# Usage: ./scripts/deploy.sh

set -e
echo "=== Deploying AgentHub ==="

# Pull latest code (when git remote is configured)
cd /opt/agenthub/backend

# Kill existing
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 2

# Start
cd /opt/agenthub/backend
nohup /opt/agenthub/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /opt/agenthub/logs/backend.log 2>&1 &

# Wait and verify
sleep 20
if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "✅ AgentHub is running"
else
    echo "❌ AgentHub failed to start"
    tail -20 /opt/agenthub/logs/backend.log
    exit 1
fi

echo "=== Deploy complete ==="
