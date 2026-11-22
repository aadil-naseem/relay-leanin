# RELAY backend

FastAPI service for the fictional Sample Precision Components demo. The application defaults to SQLite at `backend/data/fcd.sqlite`, uses the committed replay data, and can run without external API keys.

## Run locally

From the repository root:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\init_db.py
backend\.venv\Scripts\python.exe backend\scripts\reset_demo.py
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- OpenAPI UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Settings are read from `backend/.env` when present; environment variables override it. The `.env` file is intentionally ignored by Git. Gemini is optional: the committed golden drawing cache, deterministic rules, replay weather and manual passport entry are the offline paths.

## Demo controls

- Weather modes: `live`, `replay` (default), and `synthetic`.
- Read current state: `GET /api/v1/demo/state`.
- Change mode: `POST /api/v1/demo/mode` with `{"weather":"replay"}`.
- Rebuild the fictional sample world: `POST /api/v1/demo/reset`.

Replay is historical Cyclone Michaung rain shifted to the current demo clock. Exposure is a risk indicator, not a flood model; curated planning zones are not official flood maps.

## Capture the frontend offline snapshot

From `backend/`:

```powershell
.\.venv\Scripts\python.exe scripts\capture_frontend_snapshot.py
```

This captures a replay pack to `frontend/src/data/snapshot.json` using a temporary isolated SQLite database and the committed golden drawing cache. It does not change the developer demo database or call Gemini/Open-Meteo. Run it when the replay data contract changes.

## Tests and contract

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe scripts\export_openapi.py
```

The normal test run is offline and excludes the optional `live` marker. The OpenAPI snapshot is `docs/openapi.snapshot.json`. The full Phase 14 gate and its timings are recorded in `docs/TEST_REPORT.md`.
