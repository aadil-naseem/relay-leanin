"""Capture a complete, isolated replay pack for the frontend offline demo.

Run from backend with the project venv:
    .venv/Scripts/python scripts/capture_frontend_snapshot.py

The script uses a temporary SQLite database, so it never touches the developer's
live demo database. It reads the committed golden drawing cache and makes no
external provider calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
OUTPUT_PATH = REPO_ROOT / "frontend" / "src" / "data" / "snapshot.json"
DRAWING_PATH = BACKEND_DIR / "data" / "drawings" / "pump_shaft.png"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="relay-snapshot-", dir=os.getenv("TEMP") or None) as temp_dir:
        database_path = Path(temp_dir) / "snapshot.sqlite"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"

        from fastapi.testclient import TestClient

        from app.main import create_app

        try:
            with TestClient(create_app()) as client:
                call(client, "POST", "/demo/reset")
                call(client, "POST", "/demo/mode", json={"weather": "replay"})

                dashboard = call(client, "GET", "/dashboard/fac_owner")
                stress_id = dashboard["alert"]["stress_test_id"]
                stress = call(client, "GET", f"/stress-tests/{stress_id}")

                # Reuse the deterministic golden result and confirm it in this
                # isolated database so the read-only snapshot includes a complete
                # passport and redacted RFQ example.
                extracted = call(
                    client,
                    "POST",
                    "/passports/extract",
                    files={"file": ("pump_shaft.png", DRAWING_PATH.read_bytes(), "image/png")},
                )
                passport_id = extracted["passport_id"]
                call(
                    client,
                    "PATCH",
                    f"/passports/{passport_id}",
                    json={
                        "data": {
                            "quantity": 200,
                            "material": {"grade": "EN8", "standard": None, "form": None},
                            "process_route": [{"process": "TURN"}, {"process": "MILL"}],
                            "tightest_tolerance_mm": 0.02,
                        }
                    },
                )
                passport = call(client, "POST", f"/passports/{passport_id}/confirm")
                rfq = call(client, "GET", f"/passports/{passport_id}/rfq")

                matching = call(
                    client,
                    "POST",
                    "/matching/search",
                    json={"order_id": "ord_102"},
                )

                recovery = call(
                    client,
                    "POST",
                    "/recovery-requests",
                    json={"from_stress_test_id": stress_id, "order_id": "ord_102"},
                )
                recovery_id = recovery["id"]
                call(
                    client,
                    "POST",
                    f"/recovery-requests/{recovery_id}/select-partner",
                    json={"partner_id": "fac_oragadam"},
                )
                tracking = call(client, "GET", f"/recovery-requests/{recovery_id}/tracking")
                for _ in range(len(tracking["steps"])):
                    if not any(step["state"] == "PENDING" for step in tracking["steps"]):
                        break
                    tracking = call(
                        client,
                        "POST",
                        f"/recovery-requests/{recovery_id}/tracking/advance",
                    )

                recovery_request = call(client, "GET", f"/recovery-requests/{recovery_id}")
                handover = call(client, "GET", f"/recovery-requests/{recovery_id}/handover")

                # Capture the complete read-only data surface used by the demo,
                # including supporting lists fetched by the screens.
                snapshot: dict[str, Any] = {
                    "schema_version": 1,
                    "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "source": "verified replay capture · isolated demo database",
                    "data_label": "SIMULATED SAMPLE",
                    "health": call(client, "GET", "/health"),
                    "demo_state": call(client, "GET", "/demo/state"),
                    "dashboard": dashboard,
                    "stress_test": stress,
                    "spof": call(client, "GET", "/factories/fac_owner/spof"),
                    "exposure_map": call(client, "GET", "/exposure/map"),
                    "owner_exposure": call(client, "GET", "/factories/fac_owner/exposure"),
                    "readiness": call(client, "GET", "/readiness/fac_owner"),
                    "readiness_actions": call(client, "GET", "/readiness/fac_owner/actions"),
                    "readiness_history": call(client, "GET", "/readiness/fac_owner/history"),
                    "factories": call(client, "GET", "/factories"),
                    "relationships": call(client, "GET", "/factories/fac_owner/relationships"),
                    "orders": call(client, "GET", "/factories/fac_owner/orders"),
                    "parts": call(client, "GET", "/factories/fac_owner/parts"),
                    "matching": matching,
                    "recovery_request": recovery_request,
                    "recovery_tracking": tracking,
                    "recovery_handover": handover,
                    "passport": passport,
                    "rfq": rfq,
                }
        finally:
            from app.db import engine

            engine.dispose()

        OUTPUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Captured {len(snapshot) - 4} replay endpoints to {OUTPUT_PATH}")


def call(client: Any, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = client.request(method, f"/api/v1{path}", **kwargs)
    if not response.is_success:
        raise RuntimeError(f"{method} {path} failed ({response.status_code}): {response.text}")
    return response.json()


if __name__ == "__main__":
    main()
