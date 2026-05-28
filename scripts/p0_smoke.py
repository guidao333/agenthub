"""P0 smoke test for the AgentHub capability flow.

This script uses a temporary SQLite database and does not touch production data.
It verifies the local backend can:

1. start the FastAPI app,
2. expose canonical capability config templates,
3. save a customer's capability config,
4. include that config in the WebSocket capability payload,
5. create a capability chat session.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

tmp_dir = tempfile.TemporaryDirectory(prefix="agenthub-p0-")
db_path = Path(tmp_dir.name) / "agenthub_smoke.db"

os.environ["AGENTHUB_DEV"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import Capability, SessionLocal, Subscription, User, engine  # noqa: E402
from app.routes.auth import create_access_token  # noqa: E402
from app.routes.ws_client import _get_customer_capabilities  # noqa: E402


def seed_data():
    db = SessionLocal()
    try:
        customer = User(
            username="smoke_customer",
            email="smoke@example.com",
            password_hash="not-used",
            role="customer",
            status="active",
        )
        developer = User(
            username="smoke_developer",
            email="dev-smoke@example.com",
            password_hash="not-used",
            role="developer",
            status="active",
        )
        db.add_all([customer, developer])
        db.commit()
        db.refresh(customer)
        db.refresh(developer)

        isp_cap = Capability(
            developer_id=developer.id,
            cap_id="isp-smart-cs",
            name="ISP 智能客服",
            category="isp",
            status="published",
            pricing_model="monthly",
            price=299,
        )
        monitor_cap = Capability(
            developer_id=developer.id,
            cap_id="ai-smart-monitor",
            name="AI 智能监控",
            category="security",
            status="published",
            pricing_model="monthly",
            price=399,
        )
        db.add_all([isp_cap, monitor_cap])
        db.commit()
        db.refresh(isp_cap)

        sub = Subscription(
            customer_id=customer.id,
            capability_id=isp_cap.id,
            status="active",
            api_key="ahk_smoke_isp",
        )
        db.add(sub)
        db.commit()
        return customer.id, customer.username
    finally:
        db.close()


def assert_ok(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    with TestClient(app) as client:
        customer_id, username = seed_data()
        token = create_access_token({"sub": username, "role": "customer"})
        headers = {"Authorization": f"Bearer {token}"}

        health = client.get("/api/health")
        assert_ok(health.status_code == 200, f"health failed: {health.text}")

        template = client.get("/api/cap-config/templates/isp-smart-cs")
        assert_ok(template.status_code == 200, f"template failed: {template.text}")
        assert_ok("billing_url" in template.json()["schema"]["properties"], "missing billing_url template")

        before = client.get("/api/cap-config/my-config/isp-smart-cs", headers=headers)
        assert_ok(before.status_code == 200, f"my-config before failed: {before.text}")
        assert_ok(before.json()["is_configured"] is False, "fresh config should be empty")

        save = client.post(
            "/api/cap-config/save",
            headers=headers,
            json={
                "cap_id": "isp-smart-cs",
                "config": {
                    "billing_url": "http://127.0.0.1:18080",
                    "billing_username": "admin",
                    "billing_password": "secret",
                    "billing_api_type": "generic_rest",
                },
            },
        )
        assert_ok(save.status_code == 200, f"save config failed: {save.text}")

        caps = asyncio.run(_get_customer_capabilities(customer_id))
        isp = next((cap for cap in caps if cap["cap_id"] == "isp-smart-cs"), None)
        assert_ok(isp is not None, "isp capability missing from ws payload")
        assert_ok(isp["is_configured"] is True, "ws payload should include configured=true")
        assert_ok(isp["config"]["billing_url"] == "http://127.0.0.1:18080", "ws config not included")

        session = client.post(
            "/api/capability-chat/sessions",
            headers=headers,
            json={"cap_id": "isp-smart-cs"},
        )
        assert_ok(session.status_code == 200, f"create session failed: {session.text}")
        assert_ok(session.json()["cap_id"] == "isp-smart-cs", "wrong session capability")

        print("P0 smoke ok")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        tmp_dir.cleanup()
