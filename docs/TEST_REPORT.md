# Phase 14 — Backend end-to-end test gate

**Run date:** 2026-11-15

**Result:** PASS for required suites A–K and M. Optional external live smoke (L) was not run.

**Release tag:** `backend-v1` (points to the Phase 14 completion commit).
**Full regression:** 271 passed, 1 optional live test deselected. One non-blocking Starlette/httpx `TestClient` deprecation warning.

| Suite | Result | Evidence |
|---|---|---|
| A. Full regression + coverage | PASS | `pytest`; branch-aware `core/` coverage 94%, `services/` 90%. |
| B. Contract | PASS | Required `/api/v1` paths and successful response schemas checked; `docs/openapi.snapshot.json` committed and matches runtime OpenAPI. Error responses use the common envelope. |
| C. Demo story | PASS | `tests/scenario/test_demo_story.py` runs reset → replay dashboard/auto stress → SPOF → golden-cache passport/RFQ → matching → Ready partner handover/stepper → Hosur checks → readiness gain. |
| D. Failure injection | PASS | Injected forecast HTTP 500 and timeout exercise cache then replay; deleted test DB is restored by reset; empty/corrupt uploads return 422. Existing tests cover vision-provider failure → rules and manual passport fallback. |
| E. Determinism | PASS | Five reset/dashboard cycles produce identical stable dashboard payloads; repeated requests reuse the deterministic auto-test ID. |
| F. Concurrency | PASS | Ten parallel cold dashboard requests return 200 and create exactly one auto stress-test row. |
| G. Privacy | PASS | RFQ leak tests, partner consent gate, secret-not-in-logs test; `backend/.env` is Git-ignored. |
| H. Guard rails | PASS | Existing tests cover forbidden status transitions, required READY checks, STALE exclusion and reconfirm behavior. |
| I. Back-test | PASS | Michaung replay ranks all four publicly reported flooded sites above the three not-flooded sites; separation is +22. See `docs/BACKTEST_EXPOSURE.md`. |
| J. Zero-key run | PASS | End-to-end story test clears Gemini credentials and succeeds via replay, golden cache and manual/rules paths. |
| K. Performance budgets | PASS | Local replay run: dashboard cold 0.083 s / warm 0.011 s; manual stress 0.032 s; matching 0.007 s; cached passport extraction 0.025 s. All are below the specified limits. |
| L. Live external smoke | NOT RUN | Informational/optional. No fresh Open-Meteo or Gemini calls were needed for this gate. |
| M. E: drive audit | PASS | No C: cache leak. `TEMP`/`TMP` show `STALE-PROCESS`, but persisted user values point to E:. |

**Phase 14 fixes made:** concurrent dashboard requests now tolerate duplicate deterministic exposure snapshots and serialize/reuse auto stress runs; malformed image data maps to 422; the RFQ reference is generated once and matches its rendered text.

**Known non-blocking notes:** Vite/Starlette dependency warnings are documented in their respective phases. External provider availability is not certified by this offline gate.

## Follow-up fix — demo reset under concurrent reads (2026-11-15)

Found during the Phase 17 browser rehearsal: a background refetch landing inside a `POST /demo/reset` returned HTTP 500. Because an unhandled 500 is produced outside the CORS middleware, the browser reported it as a CORS failure.

- **Cause:** `reset_demo()` dropped and recreated the schema, and `compute_exposure()` wrote the deterministic snapshot row without serialization. Concurrent reads saw a missing table (`no such table`), and concurrent exposure calls either hit `UNIQUE constraint failed: exposure_snapshots.id` or `StaleDataError` on the follow-up `UPDATE`.
- **Fix:** `reset_demo()` now wipes rows instead of dropping tables (DDL is not atomic on pysqlite, so a schema window always existed) and reseeds in one transaction. A shared `app/core/locks.py:DEMO_WRITE_LOCK` serializes the reset and the exposure snapshot write; the exposure write also rolls back any earlier read transaction and retries as an insert if its row was replaced.
- **Verification:** the full `pytest` suite passes (ruff clean). A concurrency probe (20 rounds; each round = 1 reset racing 4 exposure reads) returned **80/80 HTTP 200**. A wider probe (20 rounds; reset racing dashboard, exposure, readiness, SPOF, exposure/map and health) returned **140/140 HTTP 200** with zero failures. A browser rehearsal of all eight presenter steps completed with **zero console errors**.

## Prior M2 live accuracy check (Gemini, optional `live` marker)

Run: 2026-11-14 13:41 UTC - model `gemini-3.5-flash-lite`, one call per sample PNG, JSON-output mode, temperature 0.

| Drawing | Fields correct | Latency | Detail |
|---|---:|---:|---|
| pump_shaft | 6/6 | 2.7 s | part_name: OK, drawing_no: OK, revision: OK, customer: OK, quantity: OK, material: OK |
| piston_rod | 6/6 | 3.4 s | part_name: OK, drawing_no: OK, revision: OK, customer: OK, quantity: OK, material: OK |
| valve_flange | 6/6 | 2.5 s | part_name: OK, drawing_no: OK, revision: OK, customer: OK, quantity: OK, material: OK |

**Overall accuracy: 100% (18/18) on title-block fields.** The demo uses the golden cache for the sample drawings; this optional live run is historical and was not repeated during Phase 14.
