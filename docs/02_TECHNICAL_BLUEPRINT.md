# Factory Continuity Desk — Technical Blueprint

> **Read this first.** This file is the single source of truth for **how** to build Factory Continuity Desk (FCD). The **what and why** live in `docs/01_PROJECT_BRIEF.md` (the frozen brief). Hand an AI coding agent those two files and it can build the whole project, phase by phase, with no further explanation.
>
> **Do not reopen idea selection.** The brief is frozen. This blueprint only decides *how* to build it.

---

## 0. Agent Operating Rules (apply to every phase)

| # | Rule |
|---|---|
| R1 | Read `docs/01_PROJECT_BRIEF.md`, then this file, then `docs/PROGRESS.md`. Resume at the first phase not marked DONE. |
| R2 | Work **one phase at a time, in order**. Do not start phase N+1 until every item in phase N's **Done when** passes (run its tests). |
| R3 | **Everything lives on the E: drive.** Never install, cache, create temp files, virtual environments, databases or downloads on C:. See Phase 0. Use `pathlib`; never hard-code `C:\`. |
| R4 | **Zero cost.** No paid LLMs, no paid APIs, no billing-enabled keys, no trials that need a card. Free-tier keys only. If a service asks for a card, stop and use the fallback listed in this file. |
| R5 | **Never invent external API details** (URLs, parameter names, model names, limits). Verify against the provider's live docs, then record what you verified in `docs/VERIFIED_FACTS.md`. Where this file says "verify", it is a hard stop. |
| R6 | **Pure core, thin shell.** All analytics (SPOF, scheduler, exposure score, matching, readiness, redaction) are pure functions over plain dataclasses. No DB or HTTP calls inside them. |
| R7 | **Every external dependency has a cache and a fallback** (see §3.4 Degradation Ladder). The demo must never depend on the internet being perfect. |
| R8 | **Deterministic demo.** Seed data is defined relative to the clock; `POST /api/v1/demo/reset` must return the system to the exact same starting state every time. |
| R9 | **Honest labelling.** Sample data is labelled *sample / simulated*. Risk scores are *risk indicators*, not flood predictions. A backup status can never be set to `READY` unless its required checks are done. |
| R10 | **Plain language.** Do not use words like "AI-powered", "agentic", "copilot" anywhere in UI, API text or docs. AI is used in exactly one place (reading drawings) and is described plainly (§1). |
| R11 | **Tests ship with each phase.** Commit once per phase: `phase N: <title>`. Update `docs/PROGRESS.md` at the end of every phase. |
| R12 | Hackathon rule: main project code is written during the 24 h event. Phase 0 is setup only (folders, installs, empty stubs, config). Preparation assets (sample drawings, fixtures, cached data) are allowed. |

---

## 1. What We Are Building, and Where AI Is (and Is Not) Used

**One paragraph.** FCD tells a small precision-component factory *where it would break* before a disruption, *whether a disruption is coming*, *what it would cost*, and *who could cover the work*, then keeps a *readiness score* that drops when backups go stale. Pitch line: **"Find where your factory breaks before the flood does, then show who can cover it."**

### 1.1 Where intelligence lives

| Capability | Method | Uses AI? |
|---|---|---|
| Drawing → Production Passport (M2) | Vision model reads the drawing; a deterministic text parser **cross-checks** it; a human **confirms** | **Yes. The only place.** |
| Redacted RFQ (M2) | Allow-list of fields + text template | No |
| Single-point-of-failure finder (M3) | Dependency graph and coverage analysis | No |
| Exposure engine (M4) | Rain forecast × terrain, water proximity, flood history | No |
| What-if stress test (M5) | Small scheduling simulation with downtime windows | No |
| Backup matching (M6) | Hard filters, correlated-risk exclusion, ranking | No |
| Readiness score (M8) | Formula + staleness rules | No |

**The line to use on stage:** *"Our software reads the drawing. Our maths tells you where you break."*

### 1.2 How we sell the one AI step (plain language)

1. It does the boring typing: a planner no longer re-keys material, tolerances and quantity from a drawing.
2. It is **never trusted blindly**: every field is cross-checked against a separate text parser, shown with a confidence level, and **a person confirms before anything is saved**.
3. If it fails, the form still works (manual passport). The rest of the product does not depend on it.

### 1.3 What makes FCD stand apart (use in pitch)

1. **Diagnosis before disruption.** Single points of failure come from the factory's *own* routing, not a generic checklist.
2. **Backups are checked against the same forecast.** A backup is excluded if it shares a hazard zone, cluster or power grid **or** is itself exposed to the same storm (dynamic, not just a tag).
3. **Readiness that decays.** Stale confirmations lower the score; a status cannot be faked because `READY` is guarded by completed checks.
4. **Back-tested on a real event.** The exposure score is tested against Cyclone Michaung (Chennai, Dec 2023), where the Ambattur Industrial Estate's north phase flooded and many SIPCOT estates reopened within days.
5. **IP-safe sharing.** Drawing → redacted RFQ (customer, part number, title block stripped) with permissioned sharing.
6. **Costs nothing to run** and works offline from cached data. Every number has a calculation log.

---

## 2. Hard Constraints

| Constraint | Decision |
|---|---|
| Budget | ₹0. Free-tier and open data only (cost table in §4.2). |
| Team / time | Solo, 24 h. Backend first, then a **basic** frontend. A separate frontend plan (`docs/03_FRONTEND_PLAN.md`) refines the UI later. |
| OS / drive | Windows. **All files, libraries, environments and caches on E:** (§Phase 0). |
| Frontend | React. Final landing page is a 3D scroll experience (Three.js ecosystem). Libraries are installed in Phase 0; the 3D work itself is in the separate frontend plan. |
| Testing | The phase right after the last backend phase is a rigorous end-to-end backend test gate. Frontend starts only after it passes. |
| Demo data | Fictional factories, labelled *sample / simulated*. Weather, terrain and roads are real. |

---

## 3. Architecture

### 3.1 System diagram

```
┌─────────────────────────── React (Vite, JS) ────────────────────────────┐
│ /            3D scroll landing (later, per frontend plan)                │
│ /app         dashboard · SPOF · passports · what-if · recovery · partners│
│              (Leaflet map, charts, demo controls)                        │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ JSON / REST  (/api/v1)
┌───────────────────────────────┴───────────── FastAPI (Python 3.12) ──────┐
│  routers ─► services (orchestrate, DB I/O) ─► core (PURE logic)          │
│                │                               ├ spof                    │
│                │                               ├ exposure_score          │
│                ▼                               ├ scheduler (stress)      │
│        repositories (SQLAlchemy 2.0)           ├ matching + correlation  │
│                │                               ├ readiness               │
│                │                               └ redaction (RFQ)         │
│                ▼                                                         │
│          adapters (httpx + cache + fallback) ◄── trace (calculation log) │
└───────┬────────────────┬─────────────────┬──────────────┬───────────────┘
        ▼                ▼                 ▼              ▼
   SQLite file      Open-Meteo        Prefetched JSON   Vision provider chain
   (on E:)          forecast/archive  (terrain, roads,  cache → Gemini free tier
                    + elevation        zones, replay)    → [Ollama local] → text rules
                                                         → manual form
```

### 3.2 Layer responsibilities

| Layer | Responsibility | Rule |
|---|---|---|
| `api/` (routers) | HTTP only: validate input (Pydantic), call a service, shape output | No business logic |
| `services/` | Load data from DB, call `core/`, persist results, write trace | Only layer that touches DB + adapters together |
| `core/` | Pure functions on dataclasses: SPOF, scheduler, scoring, matching, readiness, redaction | No I/O. Deterministic. Unit-testable without a DB |
| `repositories/` | SQLAlchemy queries | No logic |
| `adapters/` | Open-Meteo, vision providers, file cache | Timeouts, retries, cache, fallback; return typed results with `source` and `degraded` flags |

### 3.3 The shared spine (how modules connect)

```
M1 factories/parts/orders ──► M3 SPOF graph ───────────────┐
        │                                                  ▼
        │                           M4 exposure ──alert──► M5 stress test (auto-run)
        │                               ▲                    │ uses
        ▼                               │ same forecast      ▼
M2 passport ► part route ─────────► M6 matching ◄── correlated-risk (static tags + live exposure)
                                         │
                                         ▼
                      M7 recovery request ► M9 handover (mock) ► M10 tracking (mock)
                                         │
                                         ▼
          M8 readiness score  ◄── relationship status + checks + staleness
```

Everything reads the same tables. M4's alert **drives** M5; M5 **calls** M6 to decide whether each at-risk order has a fallback; M7 is prefilled from M5; M8 reads M6 and relationship statuses.

### 3.4 Degradation ladder (every external dependency)

| Dependency | Normal | Fallback 1 | Fallback 2 | Visible flag |
|---|---|---|---|---|
| Rain forecast | Open-Meteo forecast (live) | Last good forecast from `forecast_cache` | **Replay** of real Dec-2023 rain, time-shifted to start now | `weather.source = live \| cache \| replay \| synthetic`, `degraded` |
| Elevation | Prefetched JSON | — (static data, always local) | — | none |
| Roads / routes | Prefetched JSON | Route risk disabled; site-only exposure | — | `route_risk = null` |
| Drawing reading | Cached result (by file hash) | Gemini free tier | Local model (optional) → text-rules draft → manual form | `extraction.provider`, per-field confidence |
| Database | SQLite file | `POST /demo/reset` rebuilds from seed | — | none |

> The weather mode is switchable at runtime (`live | replay | synthetic`). **Replay** is the safe demo mode: real historical rain, honestly labelled "Replay of Cyclone Michaung rainfall (Dec 2023), time-shifted to now".

### 3.5 Time and determinism

- `core/clock.py` exposes `now()` (UTC, timezone-aware). Tests can override it. All stored datetimes are UTC; the UI shows `Asia/Kolkata`.
- Seed JSON stores **relative** times (`due_in_days`, `last_confirmed_days_ago`). The seeder converts them to absolute dates at seed time, so data never goes stale.
- The auto-run stress test is **idempotent**: keyed by `(factory_id, forecast_hash)`, so reloading the dashboard does not create duplicates.

### 3.6 Calculation log (replaces "AI reasoning traces")

Every service returns `trace: [{step, detail, inputs, output}]`. It is plain arithmetic evidence ("rolling 24 h rain 148 mm → rain hazard 0.86; site vulnerability 0.62; risk 63"). Include it in API responses for exposure, stress, matching and readiness. The UI shows it in a collapsible "How was this calculated?" panel.

---

## 4. Tech Stack

### 4.1 Choices

| Area | Choice | Why |
|---|---|---|
| Language / API | **Python 3.12** + **FastAPI** + Uvicorn | Fast to build, typed, auto OpenAPI docs, best geo/graph/PDF libs. Pin 3.12 (newer versions may lack wheels for some libs) |
| Validation / config | **Pydantic v2**, **pydantic-settings** | Strict contracts, `.env` loading |
| Database | **SQLite** (WAL mode) via **SQLAlchemy 2.0** | Zero setup, one file on E:, deterministic reset, enough for solo demo |
| HTTP client | **httpx** + **tenacity** (retry) | Timeouts, retries, easy mocking (`respx`) |
| Graph | **NetworkX** | SPOF dependency graph and road graph |
| Geo | **Shapely**, own haversine helper | Point-in-zone, distances |
| Numerics | **NumPy** | Rolling sums, percentiles |
| PDF / images | **PyMuPDF** (text layer + page render, no Poppler needed on Windows), **Pillow** | Reads PDF text, renders pages to PNG |
| Templates | **Jinja2** | RFQ text and handover pack (no AI where a template works) |
| Drawing reading | **Gemini API free tier** (Google AI Studio key, **no billing**) via plain REST (`httpx`) | Free, supports images/PDF and JSON output. Verify current free-tier model name and limits at setup |
| Optional local model | **Ollama** (vision-capable model) with models stored on E: | Offline fallback; skip if disk/time is short |
| Optional OCR | **RapidOCR (onnxruntime)** | Text for image-only drawings; skip if install is troublesome |
| Weather / elevation | **Open-Meteo** forecast, archive (historical) and elevation APIs, no key | Free for non-commercial use (fair-use limits apply; attribution required) |
| Roads / water | **OpenStreetMap** via **OSMnx** (prefetch script only) | One-time download, cached to JSON; runtime never calls Overpass |
| Sample drawings | **ReportLab** | Generate vector PDFs with a real text layer |
| Tests | **pytest**, pytest-cov, **respx**, **hypothesis**, ruff | Unit, property, contract, scenario tests |
| Frontend | **React + Vite (JavaScript)**, React Router, **TanStack Query**, **Leaflet / react-leaflet** (OSM map), a small chart lib (Recharts) | Basic UI first |
| 3D (installed now, used later) | **three**, **@react-three/fiber**, **@react-three/drei**, **gsap** | For the 3D scroll landing in the frontend plan. Match versions: R3F v9 ↔ React 19; R3F v8 ↔ React 18 |

### 4.2 Cost table

| Component | Cost |
|---|---|
| Open-Meteo (forecast, archive, elevation) | ₹0 (non-commercial, ~10k calls/day fair use; show "Weather data by Open-Meteo.com") |
| OpenStreetMap data / tiles | ₹0 (show "© OpenStreetMap contributors"; light demo use of tiles only) |
| Gemini API (free tier) | ₹0, **no billing enabled**. Note: free-tier inputs may be used by the provider to improve products → **use only synthetic/sample drawings**. A real deployment would use a local model or a paid tier with different data terms (good Q&A answer) |
| Ollama + local model (optional) | ₹0 (disk space only) |
| GitHub, Python libs, npm libs | ₹0 |

---

## 5. Repository Structure (target)

Root: `E:\Projects\factory-continuity-desk\`

```
factory-continuity-desk/
├── README.md
├── .gitignore
├── docs/
│   ├── 01_PROJECT_BRIEF.md          # copy of the frozen brief
│   ├── 02_TECHNICAL_BLUEPRINT.md    # this file
│   ├── 03_FRONTEND_PLAN.md          # separate file, supplied later
│   ├── PROGRESS.md                  # phase tracker (agent updates every phase)
│   ├── VERIFIED_FACTS.md            # external API facts verified live (R5)
│   └── TEST_REPORT.md               # produced in Phase 14
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, routers, error handlers
│   │   ├── settings.py              # pydantic-settings
│   │   ├── db.py                    # engine, session, WAL pragma
│   │   ├── enums.py
│   │   ├── errors.py                # typed errors → {"error": {code, message, details}}
│   │   ├── models/                  # SQLAlchemy ORM (one file per aggregate)
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── api/                     # routers: factories, relationships, spof, exposure,
│   │   │                            #   stress, matching, readiness, recovery, passports,
│   │   │                            #   dashboard, demo, health
│   │   ├── services/                # orchestration per module
│   │   ├── core/                    # PURE logic
│   │   │   ├── clock.py  geo.py  trace.py
│   │   │   ├── spof.py
│   │   │   ├── exposure_score.py
│   │   │   ├── scheduler.py         # list scheduler with downtime windows
│   │   │   ├── hazards.py           # hazard → downtime windows
│   │   │   ├── matching.py          # hard filters, correlation, ranking, set selection
│   │   │   ├── readiness.py
│   │   │   ├── status_rules.py      # backup status state machine + guards
│   │   │   ├── passport_rules.py    # text-rule extractor (regex) + merge + validators
│   │   │   └── redaction.py         # RFQ allow-list builder
│   │   ├── adapters/
│   │   │   ├── weather.py           # forecast/archive/replay/synthetic + cache
│   │   │   ├── vision/              # base.py, gemini.py, ollama.py, cache.py
│   │   │   └── ocr.py               # optional
│   │   └── prompts/passport_extract.md
│   ├── config/                      # YAML: exposure, stress, matching, readiness,
│   │                                #   processes, materials, cluster
│   ├── data/
│   │   ├── seed/                    # factories, vendors, parts, orders, relationships (JSON)
│   │   ├── cache/                   # terrain.json, routes.json, zones.json, replay_*.json (COMMITTED)
│   │   ├── raw/                     # raw OSM graphml etc. (git-ignored)
│   │   ├── drawings/                # sample drawings (PDF + PNG) + expected.json
│   │   ├── golden/                  # cached extraction outputs keyed by file hash (COMMITTED)
│   │   └── fcd.sqlite               # runtime DB (git-ignored)
│   ├── scripts/
│   │   ├── check_c_drive_leaks.ps1
│   │   ├── seed.py  reset_demo.py
│   │   ├── prefetch_terrain.py  prefetch_routes.py  prefetch_replay.py
│   │   ├── make_sample_drawings.py
│   │   └── smoke_connectivity.py
│   ├── tests/                       # unit/, property/, api/, scenario/, failure/, live/
│   ├── requirements.txt  requirements-dev.txt  requirements-data.txt  requirements-optional.txt
│   └── .env.example
└── frontend/                        # Vite + React (Phases 15–17)
```

---

## 6. Data Model (SQLite, SQLAlchemy 2.0)

IDs are readable string slugs for seeded rows (e.g. `fac_owner`, `ord_107`) and UUID4 strings for runtime rows.

| Table | Key columns |
|---|---|
| `factories` | id, **role** (`OWNER`\|`PARTNER`), name, is_sample, lat, lon, cluster_id, hazard_zone_id, grid_id, shift_hours_per_day (default 16), materials_handled (JSON), typical_lead_time_hours, mobilisation_hours (partners), spare_hours_per_week (JSON: process→hours, partners), contacts (JSON roles) |
| `machines` | id, factory_id, **process**, name, achievable_tolerance_mm, envelope_mm, available |
| `vendors` | id, kind (`VENDOR`\|`SUPPLIER`), name, lat, lon, cluster_id, hazard_zone_id, grid_id, process (vendors), material (suppliers), turnaround_hours |
| `vendor_links` | factory_id, vendor_id (approved vendors/suppliers of a factory) |
| `parts` | id, factory_id, name, drawing_no, customer_alias, material, is_critical, typical_batch_qty, passport_id |
| `part_steps` | id, part_id, seq, process, hours_per_unit, setup_hours, tolerance_mm (nullable), outsourced (bool) |
| `orders` | id, factory_id, part_id, qty, due_at, value_inr, customer_alias |
| `passports` | id, part_id (nullable), status (`DRAFT`\|`CONFIRMED`), data (JSON), extraction_meta (JSON), source_sha256, timestamps |
| `rfqs` | id, passport_id, rfq_ref (opaque), content (JSON), text |
| `passport_shares` | id, passport_id, partner_id, level (`RFQ`\|`FULL`), consented_at |
| `backup_relationships` | id, owner_id, partner_id, **status** (BackupStatus), last_confirmed_at, customer_approval_required, notes |
| `relationship_checks` | id, relationship_id, key (CheckKey), done, done_at |
| `hazard_zones` | id, name, center_lat, center_lon, radius_m, note |
| `site_terrain` | site_id (factory or vendor), elevation_m, ring_mean_m, relative_m, nearest_water_m, zone_ids (JSON), source, fetched_at |
| `routes` | id, site_id, exit_id, length_km, samples (JSON), low_share, underpass_count |
| `forecast_cache` | key, payload (JSON), fetched_at, source |
| `exposure_snapshots` | id, factory_id, mode, computed_at, forecast_hash, result (JSON), alert (bool) |
| `stress_tests` | id, trigger (`AUTO`\|`MANUAL`), factory_id, params (JSON), result (JSON), exposure_snapshot_id, created_at |
| `recovery_requests` | id, factory_id, order_id, stress_test_id, passport_id, status, selected_partner_id, created_at |
| `recovery_steps` | id, request_id, step_key, state, at |
| `readiness_snapshots` | id, factory_id, window_hours, score, weighted_score, breakdown (JSON), reason, computed_at |
| `app_state` | key, value (weather mode, current demo flags) |

**Enums (`enums.py`)**

```
Role: OWNER, PARTNER
ProcessCode: TURN, MILL, DRILL_TAP, GRIND_CYL, GRIND_SURF, WIRE_EDM, HEAT_TREAT, SURFACE_TREAT
BackupStatus: POTENTIAL_MATCH, ASSESSMENT_IN_PROGRESS, APPROVAL_PENDING, READY, UNAVAILABLE_EXPIRED
EffectiveStatus: BackupStatus + STALE            # computed, never stored
CheckKey: TECH_ASSESSMENT_DONE, SAMPLE_APPROVED, TERMS_AGREED, CAPACITY_RECONFIRMED, CUSTOMER_APPROVED
HazardType: FLOOD, POWER_OUTAGE, WATER_OUTAGE, ACCESS_BLOCKED, RESOURCE_DOWN
RiskLevel: LOW(<25), MODERATE(25-49), HIGH(50-74), SEVERE(>=75)
OrderState: ON_TRACK, AT_RISK, LATE
FallbackLevel: READY, POTENTIAL_ONLY, NONE
Confidence: HIGH, MEDIUM, LOW, MISSING, CONFIRMED
WeatherMode: live, replay, synthetic
```

---

## 7. Algorithm Specifications

All constants live in `backend/config/*.yaml` and are loaded once. **Do not hard-code them in logic.**

### 7.1 M3 — Single-point-of-failure finder (`core/spof.py`)

**Graph:** `Order → Part → Step(process) → Resource` where resources are in-house **machines**, approved **vendors** (outsourced steps) and **suppliers** (material). Edge `can_serve` exists if the resource can perform the step: machine process matches **and** `achievable_tolerance_mm ≤ step.tolerance_mm` (when set) **and** part envelope fits; vendor process matches; supplier material matches.

**Algorithm (coverage-based):**
1. For each active order, list its requirements: every step plus its material.
2. For each requirement, compute `servers(req)` = set of resources that can serve it.
3. For each resource `r`: remove `r`; an order is **broken** if any of its requirements now has an empty server set. Record `orders_broken`, `steps_broken`, `revenue_at_risk` = Σ `value_inr`.
4. A resource is an **SPOF** if `orders_broken` is non-empty.
5. Rank by `revenue_at_risk` desc, then order count. Flag `exposed = true` when the resource's site is inside a hazard zone or has exposure ≥ alert threshold (adds priority).
6. Output also the node/edge list so the UI can draw the dependency graph.

Machines are individual rows (a "3 lathes" form entry creates 3 rows), so two lathes are never an SPOF.

### 7.2 M4 — Exposure engine (`core/exposure_score.py`)

**Inputs per site** (factory, vendor, partner): hourly precipitation for the next 72 h (mm), terrain facts from `site_terrain`, route facts from `routes`.

```yaml
# config/exposure.yaml
horizon_hours: 72
rain_24h_breakpoints_mm:   # piecewise-linear → hazard 0..1  (IMD-style heavy / very heavy / extremely heavy bands)
  - [0, 0.0]
  - [15, 0.1]
  - [64.5, 0.5]
  - [115.6, 0.8]
  - [204.5, 1.0]
rain_3h_breakpoints_mm:    # cloudburst intensity
  - [0, 0.0]
  - [10, 0.1]
  - [30, 0.5]
  - [60, 0.85]
  - [100, 1.0]
vulnerability_weights: {depression: 0.35, water_proximity: 0.25, flood_history: 0.40}
depression_full_m: 3.0          # ≥3 m below local ring mean → 1.0
water_full_distance_m: 1500     # at/inside 0 m → 1.0, ≥1500 m → 0
vulnerability_floor: 0.25       # risk = 100 * H * (floor + (1-floor) * V)
route_weights: {low_share: 0.6, underpass: 0.4}
underpass_cap: 2
alert_threshold: 50             # HIGH and above raises the banner
heavy_onset_mm_3h: 5            # defines wet-spell start/end
recession_hours: {HIGH: 24, SEVERE: 72}   # flood water outlasts the rain
wet_spell_cap_hours: 72
cache_ttl_minutes: 10
```

**Formulas (document each in the trace):**
- `max24` = max rolling 24 h sum in the horizon; `peak3` = max rolling 3 h sum.
- `H = max(piecewise(max24, rain_24h), piecewise(peak3, rain_3h))`.
- `V = w_dep·D + w_wat·W + w_hist·Z` where `D = clamp((ring_mean − elev)/depression_full_m, 0, 1)`, `W = 1 − clamp(nearest_water_m/water_full_distance_m, 0, 1)`, `Z = 1` if the site is inside a curated historical-flood zone else `0`.
- `site_risk = round(100 · H · (floor + (1 − floor)·V))`.
- **Route risk** per access route: `V_route = clamp(0.6·low_share + 0.4·min(underpasses, cap)/cap, 0, 1)`; `route_risk = round(100·H·(floor + (1 − floor)·V_route))`. `low_share` = share of route samples below the 25th-percentile elevation of the cluster terrain grid. **Underpasses** come from OSM tunnel/negative-layer road segments.
- **Isolation risk**: if *all* exits for a site have `route_risk ≥ alert_threshold`, `isolation = true` (label: "all exit routes exposed").
- **Onset** = first hour with rolling-3 h ≥ `heavy_onset_mm_3h`; `wet_spell_hours` = last such hour − onset + 1 (capped).
- **Explainability:** return `drivers[]` in plain words ("148 mm forecast in 24 h; 2.4 m below surroundings; 380 m from water; in a historically flooded zone").

> Honest labelling: "risk indicator based on forecast rain and site conditions, **not** a flood model." Zones are *curated planning zones from public reports*, not official flood maps.

**Alert object** (when any owner-factory or its key vendor has `site_risk ≥ alert_threshold` or isolation):
```json
{"active": true, "level": "HIGH", "onset_in_hours": 36, "max_24h_mm": 148.2,
 "affected_sites": ["fac_owner", "ven_heat"], "headline": "<built by template in stress step>"}
```

### 7.3 M5 — What-if stress test (`core/hazards.py`, `core/scheduler.py`)

**Request:**
```json
{"factory_id":"fac_owner","hazard":"FLOOD","scope":{"type":"zone","ids":["zone_ambattur_north"]},
 "start_in_hours":24,"duration_hours":72}
```
Scope types: `zone` (zone ids), `cluster` (cluster ids), `grid` (grid ids), `sites` (explicit ids), `exposure_alert` (auto mode: sites whose current risk ≥ threshold), `resource` (for `RESOURCE_DOWN`).

**Hazard → effects table** (produces *downtime windows* in hours from now):

| Hazard | Who is hit | Effect |
|---|---|---|
| FLOOD | factories, vendors, suppliers in scope | All machines at the site down for `[start, start+duration]`; vendor/supplier down; dispatch and inbound blocked in the same window |
| POWER_OUTAGE | sites whose `grid_id` is in scope | Same as FLOOD |
| WATER_OUTAGE | sites in scope | Only `water_dependent` processes (HEAT_TREAT, SURFACE_TREAT) and their vendors down |
| ACCESS_BLOCKED | sites in scope | Machines keep running; dispatch, inbound material and vendor hand-offs cannot happen inside the window |
| RESOURCE_DOWN | one machine or vendor | That resource is down for the window (this is how SPOFs are demonstrated) |

**Scheduler (list scheduling with downtime, deterministic):**
- Time unit: hours from `now`. Wall-clock factor `24 / shift_hours_per_day` converts working hours to elapsed hours.
- Per order: `work = qty × hours_per_unit + setup_hours` per step. Orders are scheduled in **earliest-due-date** order. Steps run in `seq` order; a step starts at `max(previous_step_end, machine_free_at)` on the capable machine giving the earliest finish.
- Outsourced steps use a vendor: `finish = handoff_ready + turnaround_hours + transport (4 h)`, with vendor downtime applied. Material arrival uses the supplier's `turnaround_hours` (in stock → 0).
- **Finish with downtime** (pre-emptive resume):

```python
def finish_time(start, work, windows):          # windows sorted [(s, e), ...] in hours
    t, remaining = start, work
    for s, e in windows:
        if e <= t: continue
        if s > t:
            avail = s - t
            if remaining <= avail: return t + remaining
            remaining -= avail
        t = max(t, e)
    return t + remaining
```
- Run twice: **baseline** (no windows) and **stressed**. Compare each order against `due_at`.

**Order state:** `LATE` if stressed finish > due; `AT_RISK` if within `due_buffer_hours` (default 24) of due; else `ON_TRACK`.

**Result (key fields):**
```json
{"id":"…","trigger":"AUTO","hazard":"FLOOD","affected_sites":["fac_owner","ven_heat"],
 "orders":[{"order_id":"ord_107","state":"LATE","days_late":3.2,"value_inr":1200000,
            "fallback_level":"NONE","best_backup":null}],
 "summary":{"orders_at_risk":3,"revenue_exposed_inr":2150000,"orders_no_fallback":1,
            "orders_no_ready_fallback":2},
 "headline":"Heavy rain in 36h: 3 orders at risk, ₹21.5 L exposed, 1 order has no fallback",
 "trace":[…]}
```
`revenue_exposed_inr` = Σ value of `LATE` + `AT_RISK` orders. `fallback_level` per at-risk order comes from running **M6 inside the same scenario** (so correlated-risk exclusion uses this scenario's affected sites).

**Auto mode:** when M4 raises an alert, build `scope = exposure_alert`, `start_in_hours = onset`, `duration = min(wet_spell_hours, cap) + recession_hours[level]`. The banner headline is produced by a **string template** from the result summary.

### 7.4 M6 — Risk-aware backup matching (`core/matching.py`)

**Candidates:** all `PARTNER` factories. Relationship status defaults to `POTENTIAL_MATCH` if no relationship row exists.

**Hard filters** (each returns `{key, result: PASS|FAIL|UNKNOWN, basis, detail}`):

| Key | Rule | Basis |
|---|---|---|
| `process` | Partner has a machine (or approved vendor) for every step in the route | declared profile |
| `material` | Material (or its family) is in `materials_handled` | declared profile (stock unverified) |
| `tolerance` | For steps with a tolerance, a partner machine has `achievable_tolerance_mm ≤ required` | declared profile |
| `envelope` | Part envelope ≤ machine envelope | declared profile |
| `capacity` | For each process: `qty × hours_per_unit + setup ≤ spare_hours_per_week[process] × horizon/168` | declared; **UNKNOWN if last confirmed is stale** |
| `lead_time` | `mobilisation + production + logistics ≤ hours_until_deadline − buffer`, where logistics = `distance_km / 35 + 4` and production = Σ steps `qty·hpu / n_machines` × `24/shift_hours` | declared |

**Requirements not checkable in software** are always listed as `UNVERIFIED` with the check that would close them: first-article **sample approval**, **customer approval**, **agreed terms**, **inspection capability (e.g., CMM)**, **capacity reconfirmed**. A relationship's completed `relationship_checks` flip these to `VERIFIED`. *A match is a candidate, not an approved backup.*

**Correlated-risk exclusion** (config `matching.yaml`):

| Test | Result |
|---|---|
| Same `cluster_id` as the affected site | **EXCLUDED** `SAME_CLUSTER` |
| Same `hazard_zone_id` | **EXCLUDED** `SAME_HAZARD_ZONE` |
| Same `grid_id` and hazard ∈ {POWER_OUTAGE} | **EXCLUDED** `SAME_GRID` (for other hazards: down-rank, flag) |
| Partner's own `site_risk ≥ alert_threshold` in the same window | **EXCLUDED** `ALSO_EXPOSED_SAME_EVENT` (dynamic: uses the same forecast, fetched per partner location) |
| Within `min_separation_km` (default 10) of the affected site | Down-rank, flag `NEARBY` |

Excluded candidates are **still returned** (with `excluded: true` and reason) so the UI can show "technically suitable but excluded".

**Ranking** (only for candidates that pass all hard filters and are not excluded): `score = 100·(0.40·status_w + 0.20·time_slack + 0.15·capacity_slack + 0.15·freshness + 0.10·separation)`; `status_w`: READY 1.0, APPROVAL_PENDING 0.6, ASSESSMENT_IN_PROGRESS 0.4, POTENTIAL_MATCH 0.2, UNAVAILABLE_EXPIRED 0; STALE READY counts as 0.5 and is flagged "reconfirm".

**Set selection:** greedy top-k (default 2): take the best, then the next best with the smallest correlation to those chosen (different cluster, zone, grid, and not both exposed). Return `recommended_set` plus `set_correlation_note`.

**Fallback level** for an order: `READY` if a viable, non-excluded, non-stale `READY` candidate exists; else `POTENTIAL_ONLY` if any viable non-excluded candidate exists; else `NONE`.

### 7.5 M8 — Recovery Readiness Score (`core/readiness.py`, `core/status_rules.py`)

```yaml
# config/readiness.yaml
staleness_days: 90
expiring_soon_days: 14
default_window_hours: 48
windows: [24, 48, 72]
min_separation_km: 10
```

- **Critical part** = `parts.is_critical`. Weight `w = Σ value_inr of the part's open orders` (fallback 1).
- A part is **covered** within window `W` if ∃ relationship with: status `READY`, **not stale** (`now − last_confirmed_at ≤ staleness_days`), partner passes all hard filters for the part's route/material/tolerance at `typical_batch_qty`, **static non-correlation** (different cluster, hazard zone, grid; ≥ `min_separation_km` away), and `mobilisation + production + logistics ≤ W`.
- `score = 100 · Σ(w covered) / Σ(w critical)` (and an unweighted score `100 · covered / critical`). Compute for 24 / 48 / 72 h; headline = `default_window_hours`.
- **Breakdown per part:** covered? by which partner; if not covered, the reason (`NO_PARTNER_ELIGIBLE`, `NOT_READY`, `STALE`, `CORRELATED`, `TOO_SLOW`, `NO_CAPACITY`).
- **Effective status:** `READY` with `now − last_confirmed_at > staleness_days` → `STALE` ("reconfirm needed") and it does **not** count.
- **Preparedness review:** list stale partners and those expiring within `expiring_soon_days`, with a "reconfirm" action.
- **Next best actions with uplift:** for each non-counting relationship, recompute the score as if it were reconfirmed / made `READY`; return the top 5 by point gain ("Reconfirm Peenya partner → +14 pts").
- Every call writes a `readiness_snapshots` row so the UI can plot the score moving.

**Backup status state machine (`status_rules.py`)** — transitions are guarded; violations return HTTP 409:

| To status | Required checks done |
|---|---|
| `ASSESSMENT_IN_PROGRESS` | none |
| `APPROVAL_PENDING` | `TECH_ASSESSMENT_DONE` |
| `READY` | `TECH_ASSESSMENT_DONE`, `SAMPLE_APPROVED`, `TERMS_AGREED`, `CAPACITY_RECONFIRMED`, and `CUSTOMER_APPROVED` if `customer_approval_required` |
| `UNAVAILABLE_EXPIRED` | none (allowed from any state) |

Completing `CAPACITY_RECONFIRMED` or calling `reconfirm` sets `last_confirmed_at = now`.

### 7.6 M2 — Drawing → Production Passport (`adapters/vision/*`, `core/passport_rules.py`, `core/redaction.py`)

**Pipeline:**
1. **Ingest** PDF/PNG/JPG; compute SHA-256. If the hash is in `data/golden/` (or `extraction cache`), return that result instantly (marked `source: cache`).
2. **Prepare:** PDF → PyMuPDF: extract the text layer (if any) and render pages to PNG (~200 DPI, longest side ≤ 2000 px). Images are resized. Optional OCR for image-only drawings.
3. **Text rules (deterministic)** produce candidates: material (catalogue + aliases, e.g. EN8, EN24, SS304, Al6061), tolerances (`±0.05`, `+0.02/−0.00`, `H7`, "ISO 2768-m"), surface finish (`Ra 1.6`), quantity (`QTY`, `Nos`), hardness (`HRC 58–62`), title-block fields (drawing no., customer, revision), process hints by keyword (turning features, keyway/slot → MILL, holes/threads → DRILL_TAP, hardened/HRC → HEAT_TREAT, ground/Ra ≤ 0.4 → GRIND_CYL, plating/anodise/black oxide → SURFACE_TREAT).
4. **Vision reading** (provider chain) returns strict JSON per schema; **temperature 0**; "return null when a value is not visible; never guess; copy text exactly; millimetres".
5. **Merge + confidence** per field:

| Situation | Confidence |
|---|---|
| Rules and vision agree (after normalisation) | **HIGH** |
| Only one source has it and it passes catalogue/sanity validation | **MEDIUM** |
| Only one source and fails validation | **LOW** (flag) |
| Rules and vision disagree | **LOW**, show both candidates, default = rules value, flag `NEEDS_REVIEW` |
| Not found | **MISSING** (flag) |
| Edited by the user | **CONFIRMED** |

The model's own self-reported confidence is **never** used as the confidence level.
6. **Validators:** tolerance ≥ 0.001 mm; material in catalogue; quantity positive integer; units normalised to mm; dimension sanity.
7. **Human review:** `PATCH /passports/{id}` edits fields; `POST /passports/{id}/confirm` is allowed only when `process_route` ≥ 1 step, `material.grade`, `quantity`, and at least one numeric tolerance or a general-tolerance standard are non-MISSING.
8. **Fallback:** all providers fail → rules-only draft; no text layer → empty draft; the manual create endpoint always works.
9. **Redacted RFQ (no AI):** allow-list builder keeps only: process route, material + spec, envelope, tightest tolerance, surface finish, heat treatment/coating, quantity, deadline (as "days from now"), inspection requirements. **Removed:** customer name, drawing/part numbers, revision, title block, branding, free-text containing those strings (regex scrub). Output = JSON + Jinja2 text + a `redaction_report`. `rfq_ref` is an opaque random id. Partners can fetch only the RFQ unless a `passport_shares` row grants `FULL`.

**Passport JSON (fields wrap `{value, confidence, source, candidates?}`):** `part_name`, `drawing_no`, `revision`, `customer`, `process_route[]`, `material{grade, standard, form}`, `dimensions[{label, nominal_mm, tol_plus_mm, tol_minus_mm, critical}]`, `tightest_tolerance_mm` (derived), `general_tolerance_standard`, `surface_finish_ra_um`, `heat_treatment`, `coating`, `tooling_hints[]`, `quantity`, `deadline`, `inspection_notes[]`, `envelope_mm`.

> Cycle times (`hours_per_unit`) are **planner estimates** from `processes.yaml` defaults, editable in the UI. Say so on stage; a drawing does not contain cycle times.

---

## 8. API Contract (`/api/v1`)

Errors always: `{"error": {"code": "STRING", "message": "…", "details": {…}}}`. Dates are ISO-8601 UTC.

| Module | Method + path | Purpose |
|---|---|---|
| Health | `GET /health` | Liveness + DB + weather mode + vision chain status |
| M1 | `GET/POST /factories`, `GET/PUT /factories/{id}` | Owner and partner profiles |
| M1 | `POST /factories/{id}/machines`, `PUT/DELETE /machines/{id}` | Machines |
| M1 | `GET/POST /factories/{id}/orders`, `GET /factories/{id}/parts` | Orders / parts |
| M8 | `GET /factories/{id}/relationships` | Backup relationships with effective status |
| M8 | `PATCH /relationships/{id}/status` | Guarded transition (409 if checks missing) |
| M8 | `POST /relationships/{id}/checks/{key}/complete` | Mark a check done |
| M8 | `POST /relationships/{id}/reconfirm` | Refresh `last_confirmed_at` |
| M3 | `GET /factories/{id}/spof` | Ranked SPOFs + graph nodes/edges |
| M4 | `GET /factories/{id}/exposure?mode=` | Site + route risk, drivers, alert, trace |
| M4 | `GET /exposure/map` | All sites with risk for the map |
| M5 | `POST /stress-tests` | Manual test |
| M5 | `GET /stress-tests/{id}` | Result |
| M6 | `POST /matching/search` | `{order_id, scenario?}` → candidates, exclusions, recommended set |
| M7 | `POST /recovery-requests` | Manual, or `{from_stress_test_id, order_id}` prefill |
| M7 | `GET /recovery-requests/{id}` | Request + ranked options + outstanding approvals |
| M7 | `POST /recovery-requests/{id}/select-partner` | Choose partner and request activation |
| M9 | `GET /recovery-requests/{id}/handover` | Mock handover pack (data-driven) |
| M10 | `GET /recovery-requests/{id}/tracking`, `POST …/tracking/advance` | Simulated stepper |
| M8 | `GET /readiness/{factory_id}?window=48` | Score, breakdown, review list |
| M8 | `GET /readiness/{factory_id}/actions` | Next best actions with uplift |
| M8 | `GET /readiness/{factory_id}/history` | Score timeline |
| M2 | `POST /passports/extract` (multipart) | Draft passport + extraction report |
| M2 | `POST /passports/manual`, `GET/PATCH /passports/{id}`, `POST /passports/{id}/confirm` | Manual create, review, confirm |
| M2 | `GET /passports/{id}/rfq` | Redacted RFQ (JSON + text + redaction report) |
| M2 | `POST /passports/{id}/share` | Record explicit sharing consent |
| Dashboard | `GET /dashboard/{factory_id}` | **Auto-run entry point** (see §8.1) |
| Demo | `POST /demo/reset`, `POST /demo/mode {weather}`, `GET /demo/state` | Reset to seed, switch weather mode |

### 8.1 Dashboard (auto-run) contract

`GET /dashboard/{factory_id}` does, in order: (1) exposure for owner + vendors + partners (TTL-cached); (2) if alert → run or reuse the **auto stress test** (idempotent); (3) top 3 SPOFs; (4) readiness for 24/48/72; (5) stale-partner count. Returns one payload:

```json
{"factory":{…},"data_label":"SIMULATED SAMPLE",
 "weather":{"mode":"replay","source":"replay","degraded":false,"attribution":"Weather data by Open-Meteo.com"},
 "readiness":{"headline":{"window":48,"score":42,"weighted":38},"windows":{"24":30,"48":42,"72":55}},
 "alert":{"active":true,"headline":"…","onset_in_hours":36,"stress_test_id":"…","cta":"START_RECOVERY"},
 "spof_top":[…],"exposure_summary":{…},"stale_partners":1}
```

---

## 9. Demo World (build in Phase 3; labelled *sample / simulated*)

**Demo cluster (default, swappable in `config/cluster.yaml`):** Ambattur Industrial Estate, Chennai. Public reports describe the Ambattur north phase (about 1,500 units) flooded during Cyclone Michaung in Dec 2023, while several SIPCOT estates (e.g. Oragadam) resumed within days. This gives a real, documented story. Coordinates below are **starting values to sanity-check on OpenStreetMap**; factories are fictional.

| Site | Role | Approx. lat, lon | Cluster / zone / grid | Intended story role |
|---|---|---|---|---|
| Sample Precision Components (Ambattur) | OWNER | 13.100, 80.155 | `cl_ambattur` / `zone_ambattur_north` / `grid_chennai_metro` | The factory in the demo |
| Sample Heat Treat Works | VENDOR (HEAT_TREAT) | 13.105, 80.150 | same cluster/zone | **Sole** heat-treat vendor → SPOF, also exposed |
| Sample Steels (Ambattur) | SUPPLIER (EN24) | 13.095, 80.160 | same | Sole EN24 supplier |
| Sample Precision Works (Ambattur) | PARTNER | 13.098, 80.158 | same cluster + zone | Technically perfect but **EXCLUDED: same flood zone** |
| Sample Machining (Guindy) | PARTNER | 13.010, 80.212 | `cl_guindy` / `zone_guindy_adyar` / `grid_chennai_metro` | Same storm footprint → excluded or down-ranked by **live exposure** |
| Sample Components (Oragadam) | PARTNER | 12.842, 79.952 | `cl_oragadam` / — / `grid_kanchi_south` | **READY**, fresh (~40 days), the hero backup |
| Sample Engineering (Hosur) | PARTNER | 12.740, 77.830 | `cl_hosur` / — / `grid_hosur` | Technically suitable, **APPROVAL_PENDING** (missing `CUSTOMER_APPROVED`, `CAPACITY_RECONFIRMED`) |
| Sample Works (Peenya, Bengaluru) | PARTNER | 13.028, 77.520 | `cl_peenya` / — / `grid_blr` | **READY but STALE** (~120 days) → does not count |
| Sample Tools (Coimbatore) | PARTNER | 10.950, 76.970 | `cl_cbe` / — / `grid_cbe` | `POTENTIAL_MATCH`, lacks grinding at the needed tolerance |

**Owner factory:** 3 lathes (TURN), 2 VMCs (MILL), 1 drill/tap, **1 cylindrical grinder (GRIND_CYL, ±0.005 mm) → SPOF**.

**Parts (6) and orders (8)** — values in ₹, due dates relative to now:

| Part | Route | Notes |
|---|---|---|
| PRT-A Hydraulic piston rod (EN24, critical) | TURN → HEAT_TREAT (vendor) → GRIND_CYL ±0.005 | SPOF on grinder + vendor + supplier; **no partner can fully cover → "no fallback" order** |
| PRT-B Pump shaft (EN8, critical) | TURN → MILL (keyway) | **Hero order** for the recovery demo |
| PRT-C Valve body flange (SS304, critical) | MILL → DRILL_TAP | Covered by Oragadam |
| PRT-D Bracket (Al6061) | MILL | Non-critical |
| PRT-E Bushing (brass) | TURN | Non-critical |
| PRT-F Gear blank (EN8, critical) | TURN → MILL → HEAT_TREAT | Hosur-dependent |

**Story invariants (tests must assert these; tune the seed until they hold):**
1. `weather=replay` → dashboard `alert.active == true` for the owner factory.
2. Auto stress test: `orders_at_risk ≥ 2`, `revenue_exposed_inr ≥ 1,000,000`, `orders_no_fallback ≥ 1` (the PRT-A order).
3. SPOF top result is the grinder (or the heat-treat vendor); both flagged `exposed`.
4. Matching for the PRT-B hero order returns: exactly **one** viable `READY` candidate (Oragadam), **one** viable `APPROVAL_PENDING` (Hosur), **at least one** `EXCLUDED` for correlated risk (Ambattur neighbour: `SAME_HAZARD_ZONE`).
5. Peenya is `READY` but effective status `STALE`; it does not count in the score.
6. Initial readiness (48 h) is between **30 and 55**. After completing Hosur's two missing checks and setting it `READY`, the score rises by **≥ 10 points**.
7. `POST /demo/reset` ×5 yields identical dashboards.

---

## 10. Build Phases

**Timeline (agent writes code, human reviews; adjust to reality).** Hours are indicative.

| Phase | Title | Est. |
|---|---|---|
| 0 | Environment, E: drive, repo, keys | 0:50 |
| 1 | Backend skeleton | 0:40 |
| 2 | Data model and catalogues | 1:00 |
| 3 | Demo world and seeding | 1:00 |
| 4 | Real-data prefetch (terrain, routes, zones, replay) | 1:15 |
| 5 | M1 — profiles, orders, relationships API | 0:45 |
| 6 | M3 — SPOF finder | 0:55 |
| 7 | M4 — Exposure engine and alert | 1:40 |
| 8 | M5 — Stress test | 1:40 |
| 9 | M6 — Backup matching | 1:15 |
| 10 | M8 — Readiness, statuses, preparedness | 1:15 |
| 11 | M7, M9, M10 — Recovery request and mocks | 0:50 |
| 12 | M2 — Passport extraction and RFQ | 2:00 |
| 13 | Orchestration: dashboard, demo controls | 0:40 |
| **14** | **Backend end-to-end test gate** | **1:30** |
| 15 | Frontend setup | 0:40 |
| 16 | Basic frontend screens | 2:00 |
| 17 | Integration test (UI ↔ API) | 0:45 |
| 18 | Freeze, rehearsal, submission | 0:45 |

**If behind schedule, cut in this order:** M10 stepper → M9 handover → OCR → Ollama → route-based exposure (keep site-only) → POWER/WATER hazards. **Never cut:** M1–M8 and the testing gate.

---

### PHASE 0 — Environment, E: Drive, Repo, Keys

**Goal:** A clean, working workspace entirely on **E:**, every tool installed and verified, repo created, keys obtained, connectivity proven. **No application code is written here.**

> **E: DRIVE RULE.** The project, every library, every virtual environment, every cache, every temp file, every download and every model must be on **E:**. The C: drive has storage problems; a single large install landing there can break the build. Follow every step below and run the leak audit at the end.

**0.1 Create the folder layout on E:**

```powershell
New-Item -ItemType Directory -Force E:\Projects\factory-continuity-desk | Out-Null
New-Item -ItemType Directory -Force E:\dev-cache\pip, E:\dev-cache\npm, E:\dev-cache\npm-global, E:\dev-cache\temp, E:\dev-cache\ollama, E:\dev-cache\huggingface, E:\dev-cache\playwright, E:\dev-cache\osmnx | Out-Null
Set-Location E:\Projects\factory-continuity-desk
```

**0.2 Redirect caches and temp to E: (user-level, persistent).** Close and reopen all terminals and the editor afterwards.

```powershell
[Environment]::SetEnvironmentVariable("PIP_CACHE_DIR","E:\dev-cache\pip","User")
[Environment]::SetEnvironmentVariable("TEMP","E:\dev-cache\temp","User")
[Environment]::SetEnvironmentVariable("TMP","E:\dev-cache\temp","User")
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS","E:\dev-cache\ollama","User")
[Environment]::SetEnvironmentVariable("HF_HOME","E:\dev-cache\huggingface","User")
[Environment]::SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH","E:\dev-cache\playwright","User")
[Environment]::SetEnvironmentVariable("npm_config_cache","E:\dev-cache\npm","User")
[Environment]::SetEnvironmentVariable("npm_config_prefix","E:\dev-cache\npm-global","User")
```
Add `E:\dev-cache\npm-global` to the user `PATH`.

**0.3 Install tools, choosing E: paths in each installer.**
- **Python 3.12** → install to `E:\Python312` (Custom install; tick *Add to PATH*). Check `python --version` and `where python` point to E:.
- **Node.js (current LTS)** → install to `E:\nodejs`. Check `node -v`, `npm -v`.
- **Git** → install to `E:\Git`. Set `git config --global user.name / user.email`.
- **Optional, only if ≥ 6 GB free on E: and time allows:** Ollama (its models go to `OLLAMA_MODELS` on E:).
- Do **not** run `Set-ExecutionPolicy` globally; call the venv's Python directly (`.\.venv\Scripts\python.exe`) so no activation script is needed.

**0.4 Create the Python environment on E: and install libraries**

```powershell
Set-Location E:\Projects\factory-continuity-desk\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```
Create the requirement files, then install:

- `requirements.txt`: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy>=2.0`, `httpx`, `tenacity`, `pyyaml`, `networkx`, `numpy`, `shapely`, `jinja2`, `python-multipart`, `pymupdf`, `pillow`, `python-dotenv`
- `requirements-dev.txt`: `pytest`, `pytest-cov`, `respx`, `hypothesis`, `ruff`
- `requirements-data.txt` (prefetch + sample drawings): `osmnx`, `reportlab`
- `requirements-optional.txt`: `rapidocr-onnxruntime`

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-data.txt
```
Set `OSMNX` cache folder to `E:\dev-cache\osmnx` in the prefetch scripts (never use its default location).

**0.5 Frontend scaffold and libraries on E:**

```powershell
Set-Location E:\Projects\factory-continuity-desk
npm create vite@latest frontend -- --template react
Set-Location frontend
npm install
npm install react-router-dom @tanstack/react-query leaflet react-leaflet recharts three @react-three/fiber @react-three/drei gsap
```
If `@react-three/fiber` reports a React peer-version conflict, use R3F v9 with React 19, or R3F v8 with React 18. Do not install a UI component kit.

**0.6 Git and GitHub**
1. `git init` in the project root; create `.gitignore` (`.venv/`, `node_modules/`, `.env`, `backend/data/fcd.sqlite*`, `backend/data/raw/`, `__pycache__/`, `.pytest_cache/`, `dist/`).
2. Create an empty GitHub repo `factory-continuity-desk` (via the GitHub site or `gh repo create` if installed), add it as `origin`, make the first commit and push.
3. **Do commit** `backend/data/cache/` and `backend/data/golden/` (small, derived, needed for offline demo).

**0.7 Project docs and stubs.** Copy the brief to `docs/01_PROJECT_BRIEF.md` and this file to `docs/02_TECHNICAL_BLUEPRINT.md`. Create empty `docs/PROGRESS.md` (a checklist of phases 0–18) and `docs/VERIFIED_FACTS.md`. Create the folder tree from §5 with empty files (one-line docstring each). Create `.env.example` (Appendix A) and copy it to `.env`.

**0.8 Keys and accounts (free only)**
1. **Gemini:** open Google AI Studio, create an API key **without enabling billing**. Put it in `.env` as `GEMINI_API_KEY`. In AI Studio, note which Flash-class model lists free-tier access and its current limits; set `GEMINI_MODEL` accordingly and record both in `docs/VERIFIED_FACTS.md`.
2. Open-Meteo and OSM need **no key**.
3. GitHub repo from 0.6.

**0.9 Connectivity smoke test** (`scripts/smoke_connectivity.py`, the only code in this phase, a throw-away script): (a) one Open-Meteo forecast call; (b) one Open-Meteo archive call for 2023-12-03; (c) one Open-Meteo elevation call; (d) one Gemini call with a tiny test image returning JSON. Log request/response shapes into `docs/VERIFIED_FACTS.md`. If (d) fails or quota is unavailable, note it; the fallback chain still works.

**0.10 C: drive leak audit** (`scripts/check_c_drive_leaks.ps1`). It must print and verify:
```powershell
pip cache dir ; npm config get cache ; npm config get prefix ; echo $env:TEMP ; where.exe python ; where.exe node
# and report size of: $env:LOCALAPPDATA\pip, $env:APPDATA\npm-cache, $env:LOCALAPPDATA\Temp
```
All paths must start with `E:\`. If anything points to `C:\`, fix it before moving on.

**Done when:** `python --version` and `node -v` work from E:; `pip install` and `npm install` completed with no new data landing on C: (audit script passes); repo pushed to GitHub; `.env` has the Gemini key; smoke test results are in `docs/VERIFIED_FACTS.md`; folder tree matches §5.

---

### PHASE 1 — Backend Skeleton

**Goal:** A running FastAPI app with config, DB session, clock, errors, trace helper and a green test run.

**Tasks**
1. `settings.py` (pydantic-settings; reads `.env`): DB path (absolute, on E:), `WEATHER_MODE`, `GEMINI_*`, `VISION_PROVIDER_CHAIN`, CORS origins (`http://localhost:5173`), `STALENESS_DAYS`.
2. `db.py`: SQLAlchemy engine for `sqlite:///E:/…/fcd.sqlite`, `PRAGMA journal_mode=WAL`, `foreign_keys=ON`; session dependency.
3. `core/clock.py`, `core/geo.py` (haversine, point-in-circle), `core/trace.py` (`TraceBuilder.add(step, detail, inputs, output)`).
4. `errors.py` + global handler producing the standard error shape.
5. `main.py`: app, CORS, `/api/v1` router prefix, `GET /api/v1/health`.
6. Config loader: reads every YAML in `config/` once into typed objects (§7 YAML blocks).
7. `pytest` setup (`conftest.py` with an isolated temp DB under E:), first tests: health endpoint, clock override, haversine known distance.

**Done when:** `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` serves `/docs`; `pytest` is green; `ruff` clean.

---

### PHASE 2 — Data Model and Catalogues

**Goal:** All tables, enums, Pydantic schemas and YAML catalogues exist.

**Tasks**
1. ORM models for every table in §6; `scripts/init_db.py` creates tables (no Alembic needed).
2. `enums.py` exactly as in §6.
3. Catalogues:
   - `config/processes.yaml`: for each ProcessCode: `default_hours_per_unit`, `default_setup_hours`, `water_dependent`, typical `achievable_tolerance_mm` range. (Starting values: TURN 0.10 h/unit, MILL 0.15, DRILL_TAP 0.05, GRIND_CYL 0.12, HEAT_TREAT batch-based vendor, etc.)
   - `config/materials.yaml`: grade, family, aliases (regex-ready): EN8, EN24, EN19, C45, SS304, SS316, Al6061, Al6082, Brass (IS 319), Mild Steel, Delrin, Ti-6Al-4V.
4. Pydantic schemas for requests/responses of every endpoint in §8 (shapes first; logic later).
5. Write all YAML config files from §7 (`exposure`, `stress`, `matching`, `readiness`, `cluster`).
6. Tests: model round-trip, enum coverage, YAML schema validation (fail fast on bad config).

**Done when:** `init_db.py` builds an empty DB; config loader validates all YAML; tests green.

---

### PHASE 3 — Demo World and Seeding

**Goal:** The §9 demo world exists as seed JSON, with a one-command reset.

**Tasks**
1. Author `data/seed/*.json` per §9 (owner, 2 vendors/suppliers, 6 partners, machines, 6 parts with steps, 8 orders, relationships with checks). Use **relative times** (`due_in_days`, `last_confirmed_days_ago`).
2. Relationship setup: Oragadam `READY` with all checks done (confirmed ~40 days ago); Hosur `APPROVAL_PENDING` with `TECH_ASSESSMENT_DONE`, `SAMPLE_APPROVED`, `TERMS_AGREED` done and `CUSTOMER_APPROVED`, `CAPACITY_RECONFIRMED` **not** done; Peenya `READY` confirmed ~120 days ago; Coimbatore `POTENTIAL_MATCH`; Ambattur neighbour and Guindy `ASSESSMENT_IN_PROGRESS` or `READY` (so exclusion is the reason they are not used, not their status).
3. `scripts/seed.py` + `scripts/reset_demo.py` (drop/recreate, seed, write an initial readiness snapshot). Expose later as `POST /demo/reset`.
4. Mark everything `is_sample = true`.
5. Tests: seed loads without FK errors; counts match; dates are relative to the overridden clock; reset twice gives identical rows.

**Done when:** `reset_demo.py` runs in < 3 s and produces the §9 entities. (Story invariants that depend on later modules are verified in their own phases.)

---

### PHASE 4 — Real-Data Prefetch (terrain, routes, zones, replay)

**Goal:** All real-world data the engines need is downloaded **once**, reduced to small JSON, and committed, so runtime needs no internet except the live forecast.

**Tasks**
1. **Sites to cover:** every factory, vendor, supplier, plus the back-test sites in `config/cluster.yaml` (flooded: Ambattur north, Villivakkam, Thirumudivakkam, Perungudi; not flooded: Oragadam, Irungattukottai, Pillaipakkam; coordinates are approximate starting values, verify on OSM).
2. `prefetch_terrain.py`: for each site, sample elevation at the centre and on 3 rings (500 m, 1000 m, 2000 m) × 8 bearings using the **Open-Meteo elevation API** (batch ≤ 100 coordinates per call; **verify** parameters). Compute `ring_mean_m`, `relative_m = elev − ring_mean`. Also sample a coarse grid over the cluster bounding box (≈ 15×15) and store its 25th-percentile elevation as `low_threshold_m`.
3. `prefetch_routes.py`: with **OSMnx** (cache dir on E:), download the drivable network around the Ambattur area once (store raw graph under `data/raw/`, git-ignored). Nearest water distance: from OSM waterways/water bodies. For each site and each configured **exit** (2–3 junctions in `cluster.yaml`), compute the shortest route, sample every ~250 m, fetch elevations (batched), flag samples below `low_threshold_m`, count underpass segments (tunnel or negative layer). Write compact `routes.json` + `site_terrain` data into `data/cache/`.
4. `zones.json`: curated **historical flood zones** as circles (center, radius) for the Ambattur north phase and the other back-test flooded estates, with a `note` citing the public reporting. Label them "illustrative planning zones".
5. `prefetch_replay.py`: via the Open-Meteo **archive** API fetch hourly precipitation for the replay window (start around 2023-12-01 to 2023-12-07) at each site; save `replay_michaung.json`. Choose the shift so the heavy onset appears ~24–40 h after the window start. **Verify** the data actually shows heavy rain; if the archive is too smooth, keep it but also build `synthetic_storm.json` (a labelled synthetic profile) as the last-resort mode.
6. Seeder loads the cached JSON into `site_terrain`, `routes`, `hazard_zones`.
7. Tests: JSON schema checks; every site has terrain; every route has ≥ 10 samples; replay series length = window hours; **no network used at test time**.

**Done when:** `data/cache/` is populated and committed; a fresh clone plus `reset_demo.py` works with the internet disabled.

---

### PHASE 5 — M1: Profiles, Orders, Relationships API

**Goal:** CRUD for factories (owner/partner), machines, orders, parts, relationships, checks.

**Tasks**
1. Routers + services per §8 (M1 rows). Creating a machine with `count = N` creates N rows.
2. `core/status_rules.py` state machine and guards (§7.5). `PATCH /relationships/{id}/status` returns 409 with `details.missing_checks`.
3. `POST /relationships/{id}/checks/{key}/complete` and `POST /relationships/{id}/reconfirm`.
4. Effective status (`STALE`) computed at read time.
5. Tests: illegal transitions → 409; `READY` blocked without all checks; reconfirm updates date; CRUD validation errors use the standard error shape.

**Done when:** Every M1 endpoint works against the seeded DB; the guard tests pass.

---

### PHASE 6 — M3: SPOF Finder

**Goal:** `GET /factories/{id}/spof` returns the ranked SPOF list and graph.

**Tasks**
1. `core/spof.py` per §7.1 (pure; input dataclasses, output ranked list + nodes/edges).
2. `services/spof.py` loads orders, steps, machines, vendors, suppliers and the exposure flag (zone membership; live exposure joined later in Phase 13).
3. Router + response schema including `trace`.
4. **Tests:** (a) hand-built tiny graph with known SPOFs; (b) **property test (hypothesis)** comparing the algorithm with a brute-force "remove each resource and re-check" implementation; (c) seeded world: grinder and heat-treat vendor appear, three lathes never do.

**Done when:** The seeded world's top SPOF matches §9 invariant 3; property tests pass.

---

### PHASE 7 — M4: Exposure Engine and Alert

**Goal:** Real forecast in, explained risk scores and an alert out.

**Tasks**
1. `adapters/weather.py`: `get_hourly_precip(sites, mode)` with modes `live | replay | synthetic`; live = Open-Meteo forecast (batch multi-location; **verify** params); write each good response to `forecast_cache`; on failure use the cache; then replay; each result carries `source` and `degraded`. Replay shifts the stored series so index 0 = `now()`.
2. `core/exposure_score.py` per §7.2: rolling sums, `H`, `V`, site risk, route risk, isolation, onset, wet-spell, drivers, alert object.
3. `services/exposure.py`: TTL cache (`cache_ttl_minutes`), writes `exposure_snapshots`, returns trace.
4. Router: `GET /factories/{id}/exposure?mode=`, `GET /exposure/map`; `POST /demo/mode` (store in `app_state`).
5. **Tests:** pure-function tests with hand-computed numbers (e.g., 148 mm → hazard 0.86); route risk with and without underpasses; alert threshold edge cases; forecast failure → fallback chain with correct flags (using `respx`).
6. **Back-test (report, not just assert):** run replay on the back-test sites; print a ranking table. Expect flooded sites to rank above non-flooded ones. If not, tune weights in `exposure.yaml` (not code) and record what changed in `docs/VERIFIED_FACTS.md`. Never tune by hard-coding site names.

**Done when:** In `replay` mode the owner factory is `HIGH` or above with readable drivers; Oragadam scores lower than Ambattur; the back-test table is saved to `docs/`.

---

### PHASE 8 — M5: What-If Stress Test (manual + auto)

**Goal:** Hazard → downtime windows → baseline vs stressed schedule → at-risk orders and revenue.

**Tasks**
1. `core/hazards.py`: scope resolution and hazard → downtime windows (§7.3 table).
2. `core/scheduler.py`: `finish_time`, EDD list scheduler with machine and vendor resources, supplier lead time, dispatch blocking for `ACCESS_BLOCKED`.
3. `services/stress.py`: builds inputs from DB, runs baseline and stressed, computes order states and summary, calls the M6 matcher for fallback levels (**stub returns `NONE` until Phase 9; wire it properly in Phase 9**), stores `stress_tests`.
4. Auto-run function `run_auto_for_alert(exposure_snapshot)`: idempotent on `(factory_id, forecast_hash)`; builds the headline from a template.
5. Router: `POST /stress-tests`, `GET /stress-tests/{id}`.
6. **Tests:** `finish_time` cases (no window, window before, during, after, multiple windows); scheduler invariants with hypothesis (stressed finish ≥ baseline finish; no resource double-booked; step order respected); a hand-computed 2-order example; each hazard type affects the intended resources only; idempotent auto-run.

**Done when:** A manual FLOOD test on the owner factory produces LATE orders with sensible dates; the auto test attaches to the alert; scheduler property tests pass.

---

### PHASE 9 — M6: Risk-Aware Backup Matching

**Goal:** Ranked candidates with checked vs unverified requirements and correlated-risk exclusion.

**Tasks**
1. `core/matching.py` per §7.4: hard filters with `PASS/FAIL/UNKNOWN`, `UNVERIFIED` list, correlation tests (static tags + dynamic exposure), ranking, greedy set selection, `fallback_level`.
2. `services/matching.py`: loads candidates, relationships, part routes; gets each partner's live `site_risk` from the exposure service for the scenario window (same forecast).
3. Router: `POST /matching/search`; replace the Phase 8 stub so stress results carry real `fallback_level` and `best_backup`.
4. **Tests:** each filter pass/fail case; every exclusion reason; set selection avoids correlated pairs; seeded hero order meets §9 invariant 4; the PRT-A order has `fallback_level = NONE` (invariant 2 re-checked end to end).
5. Tune **seed data** (not logic) until invariants hold; document any change.

**Done when:** Invariants 2 and 4 pass in replay mode; the response shows, per candidate, which requirements were checked and which remain unverified.

---

### PHASE 10 — M8: Readiness Score, Preparedness, Next Best Actions

**Goal:** The computed score that moves when statuses or staleness change.

**Tasks**
1. `core/readiness.py` per §7.5 (covered logic, windows, weighted and unweighted score, per-part reasons).
2. `services/readiness.py`: loads data, computes 24/48/72, writes `readiness_snapshots`, builds the preparedness review (stale / expiring) and **next-best-actions with uplift** (counterfactual recompute).
3. Router: `GET /readiness/{id}`, `/actions`, `/history`. Snapshot also on every status change or reconfirm.
4. **Tests:** score by hand for a 3-part example; stale partner excluded; reconfirm raises score; completing checks and setting `READY` raises score; uplift numbers equal the real delta after applying the action; invariants 5 and 6.

**Done when:** Invariants 5 and 6 pass; `actions` shows a plausible top action whose predicted uplift equals the real change when executed.

---

### PHASE 11 — M7, M9, M10: Recovery Request and Mocks

**Goal:** Prefilled recovery request, ranked options, mock handover pack and tracking stepper.

**Tasks**
1. `POST /recovery-requests` accepts `{from_stress_test_id, order_id}` (prefills disruption, order, quantity, deadline, passport) or manual input.
2. `GET /recovery-requests/{id}`: includes M6 options, readiness status, capacity, outstanding approvals ("CUSTOMER_APPROVED pending").
3. `POST …/select-partner`: records selection and a request-sent step. Text must say activation is subject to human, customer and contractual approvals outside the software.
4. **Mocks (clearly labelled simulated):** `GET …/handover` builds the pack from data with Jinja2 (job requirements, authorised documents list, quantity/deadline, inspection checklist, contacts, required approvals, milestones). Tracking steps: `REQUEST_SENT → PARTNER_RESPONSE → TECHNICAL_AND_CUSTOMER_APPROVALS → PRODUCTION_SCHEDULED → PRODUCTION_STARTED → QUALITY_INSPECTION → DISPATCH_AND_DELIVERY`; `POST …/tracking/advance` moves one step.
5. Tests: prefill correctness; cannot select an excluded partner (409); stepper order; handover contains no redacted fields for a partner without consent.

**Done when:** The §9 demo steps 5–6 work through the API.

---

### PHASE 12 — M2: Production Passport Extraction and Redacted RFQ

**Goal:** Drawing in → reviewed, confirmed passport → redacted RFQ. Fully functional **without** any AI via the manual path.

**Tasks**
1. `scripts/make_sample_drawings.py` (ReportLab): produce **3 synthetic drawings** (pump shaft, piston rod, valve flange) as vector PDFs **with a text layer**, plus a rasterised PNG version of each and one deliberately messy variant (rotated / low-contrast). Each has a title block (fictional customer "ACME Hydraulics (SAMPLE)", drawing no., revision), material, tolerances, finish, quantity, notes. Write `expected.json` ground truth per drawing. (Synthetic only, because free-tier inputs may be used by the provider.)
2. `core/passport_rules.py`: regex/catalogue extractor, normaliser, validators, merge + confidence (§7.6).
3. `adapters/vision/`: `VisionProvider` interface; `cache.py` (golden results by SHA-256); `gemini.py` (plain REST via `httpx`; **verify** the request shape, JSON-output config and model name in the current docs; temperature 0; timeout ~30 s; one retry on 429/5xx; 10-minute cooldown after quota errors); `ollama.py` (optional); chain order from `VISION_PROVIDER_CHAIN`.
4. `prompts/passport_extract.md`: plain instructions (null if not visible; never guess; copy printed text exactly; millimetres; return only JSON matching the schema).
5. `services/passport.py`: ingest → prepare → rules + vision → merge → store draft with `extraction_meta` (provider, latency, source). Save successful vision results into `data/golden/`. Pre-generate golden outputs for the 3 sample drawings so the demo never depends on the network.
6. `core/redaction.py` + Jinja2 RFQ text; `redaction_report`; `passport_shares` consent gate (partner gets RFQ only unless `FULL` consent).
7. Routers per §8 (M2 rows). Confirm creates or updates the part and its `part_steps` (default cycle times from `processes.yaml`, editable).
8. **Tests:** rules-only accuracy on the vector PDFs against `expected.json` (target ≥ 80 % of critical fields); merge-confidence table cases; vision failure → rules draft; **RFQ leak test**: assert customer name, drawing number, part number never appear in RFQ JSON or text across all fixtures; consent gate returns 403; cached extraction returns in < 3 s.
9. Live accuracy check (marked `@pytest.mark.live`, optional): run Gemini on the 3 PNGs and record accuracy in `docs/TEST_REPORT.md`.

**Done when:** All three sample drawings produce confirmed passports (via cache or live) and clean RFQs; the manual path works with all vision providers disabled.

---

### PHASE 13 — Orchestration: Dashboard and Demo Controls

**Goal:** The single auto-run entry point and demo reliability tools. **Last backend phase.**

**Tasks**
1. `GET /dashboard/{factory_id}` per §8.1; joins live exposure into SPOF `exposed` flags; reuses the idempotent auto stress test.
2. `POST /demo/reset`, `POST /demo/mode`, `GET /demo/state`.
3. OpenAPI polish: tags, summaries, examples for the main payloads; a short `backend/README.md` (run, reset, modes).
4. Response size and speed check (§Phase 14 budgets).

**Done when:** One call to the dashboard in `replay` mode returns the banner, readiness, top SPOFs and the auto stress summary; reset then dashboard is repeatable.

---

### PHASE 14 — BACKEND END-TO-END TEST GATE (rigorous)

**Goal:** Prove the backend is complete and demo-safe **before any frontend work**. **No frontend phase starts until every item below passes.**

**Suites**

| Suite | What it proves |
|---|---|
| A. Full regression | All unit + property tests from Phases 1–13 pass; coverage ≥ 80 % on `core/` and `services/` |
| B. Contract | Every endpoint in §8 returns a body that validates against its response schema; OpenAPI snapshot saved; error shape is uniform |
| C. **Demo-story scenario** (`tests/scenario/test_demo_story.py`) | Runs the 7-step story via `TestClient` in `replay` mode with cached data and vision chain = cache: dashboard alert → auto stress → SPOF → passport + RFQ → recovery request prefill → matching (Ready / Approval Pending / Excluded) → select Ready partner → handover + stepper → complete Hosur checks → `READY` → score up. Asserts **all §9 invariants** |
| D. Failure injection | Forecast 500 / timeout → cache with `degraded=true`; no cache → replay; all vision providers fail → rules draft → manual works; DB deleted → `reset_demo` restores; malformed upload → 422 not 500 |
| E. Determinism | `reset` ×5 → identical dashboards (compare JSON minus timestamps/ids); auto stress not duplicated across 10 reloads |
| F. Concurrency | 10 parallel dashboard requests: no 500s, one auto stress row |
| G. Privacy | RFQ leak test over all fixtures; partner cannot read the full passport without consent; no secrets in logs; `.env` is git-ignored |
| H. Guard rails | Illegal status transitions → 409; `READY` impossible without checks; stale partner excluded from score; reconfirm restores it |
| I. Back-test | Michaung table: flooded sites rank above non-flooded; saved to the report (honest result, even if imperfect) |
| J. Zero-key run | With **no** API keys in the environment, the whole scenario suite still passes (cache/replay/manual paths) |
| K. Performance budgets | Dashboard warm < 1.5 s, cold < 6 s; stress test < 2 s; matching < 1 s; cached passport < 3 s |
| L. Live smoke (optional marker) | Real Open-Meteo forecast works; one real Gemini extraction works; results logged |
| M. E: drive audit | Run `check_c_drive_leaks.ps1` after the full test run: no new files on C: |

**Deliverables:** `docs/TEST_REPORT.md` (pass/fail per suite, timings, back-test table, live-smoke notes, known limitations), git tag `backend-v1`.

**Done when:** Suites A–K and M pass (L is informational). Any failure is fixed and the whole gate re-run. Only then continue.

---

### PHASE 15 — Frontend Setup

**Goal:** React app shell wired to the verified backend. **Basic UI only; the separate frontend plan will refine visuals later.**

**Tasks**
1. Use the Vite project from Phase 0. Structure: `src/api/` (fetch client with base URL from `VITE_API_URL`, TanStack Query hooks per endpoint), `src/pages/`, `src/components/`, `src/routes.jsx`.
2. Routes: `/` (simple landing placeholder with a "Open the app" button; **reserve the layout for the later 3D scroll landing**, with `three` and `@react-three/fiber` already installed but unused), `/app` shell with nav: Dashboard, SPOF, Passports, What-if, Recovery, Partners, Demo controls.
3. Global components: `DataLabelBadge` ("SAMPLE / SIMULATED"), `WeatherSourceBadge` (live / replay / cache / synthetic with `degraded` flag), `CalcLog` (collapsible trace), `StatusPill`, `RiskPill`, `Money` (₹ lakh/crore formatting), footer attributions ("Weather data by Open-Meteo.com", "© OpenStreetMap contributors").
4. Vite dev proxy or CORS to `http://localhost:8000`.

**Done when:** `npm run dev` on port 5173 renders the shell and `GET /health` shows in a status chip.

---

### PHASE 16 — Basic Frontend Screens

**Goal:** Every module reachable and usable, plain styling.

| Screen | Content | Endpoints |
|---|---|---|
| Dashboard | Readiness gauge (24/48/72 toggle), **alert banner** with "Start Recovery Request", top 3 SPOFs, Leaflet map with site risk markers | `/dashboard/{id}`, `/exposure/map` |
| SPOF | Ranked table + simple dependency graph (nodes/edges) | `/factories/{id}/spof` |
| Passports | Upload → draft with confidence chips → inline edit → Confirm → RFQ view (with "what was removed") | `/passports/*` |
| What-if | Hazard, zone/scope, start, duration form → result table with order states and fallback levels | `/stress-tests` |
| Recovery | Prefilled request, candidate cards (Ready / Approval Pending / Excluded with reason, checked vs unverified), select partner, handover pack, stepper | `/recovery-requests/*`, `/matching/search` |
| Partners | Relationship table with effective status, checks, Reconfirm button, next-best-actions, score history chart | `/factories/{id}/relationships`, `/readiness/*` |
| Demo controls | Weather mode switch, Reset | `/demo/*` |

**UI copy rules:** plain words ("checked", "unverified", "reconfirm needed", "reads your drawing"). No "AI-powered".

**Done when:** The full demo story can be performed in the browser end to end with the backend in `replay` mode.

---

### PHASE 17 — Frontend ↔ Backend Integration Test

**Tasks**
1. Run the 7-step demo story manually in the browser three times, including `Demo controls → Reset` between runs.
2. Optional: one Playwright smoke test (browsers stored under `E:\dev-cache\playwright`).
3. Fix contract mismatches (backend contract is authoritative; adjust the client unless a real bug is found, then fix and re-run the Phase 14 scenario test).
4. Verify attributions, sample labels and degraded-mode badges are visible.

**Done when:** Three consecutive clean runs with zero console errors and no manual database edits.

---

### PHASE 18 — Freeze, Rehearsal, Submission

**Tasks**
1. Tag `v1.0`; update README (what it is, how to run on Windows from E:, demo steps, limitations). Update `docs/PROGRESS.md`.
2. **Demo script (3–4 min)** following brief §9, with the line "our software reads the drawing; our maths tells you where you break". Rehearse twice. Keep `replay` mode as default and a pre-opened tab for each screen.
3. **Q&A prep (short answers):**
   - *Where is AI used?* Only to read drawings; cross-checked, confirmed by a person; the manual form still works.
   - *Why not use it everywhere?* Calculations must be explainable and repeatable; every number has a calculation log.
   - *Isn't it just a marketplace?* The product leads with diagnosis; matching is the last step and is correlated-risk aware.
   - *How accurate is the exposure score?* A risk indicator back-tested on Michaung; not a flood model; show the back-test table.
   - *Cold start / adoption?* Pilot with one cluster; diagnosis is useful before any backup joins.
   - *Data sharing / IP?* Redacted RFQ and permissioned sharing; free-tier model used on sample drawings only; a real deployment would use a local model.
   - *Competitors?* Verify Xometry, Fictiv, Zetwerk, Resilinc, Everstream, Interos briefly before pitching; position the **combined workflow**.
4. **Submission checklist:** track = Open Innovation; repo link; README; demo video if required; sample data labelled; attributions present; submitted well before the deadline.

**Done when:** Two timed rehearsals under 4 minutes; repo is public/shared as required; nothing depends on a key that could fail on stage.

---

## 11. Risks and Mitigations (engineering)

| Risk | Mitigation |
|---|---|
| Gemini free quota or model name changes | Verify in Phase 0; golden cache for the 3 demo drawings; rules-only draft; manual form |
| Open-Meteo down or rate-limited | `forecast_cache` → replay → synthetic; mode switch in demo controls |
| OSMnx install pain on Windows | Prefetch is one-time; if it fails, ship site-only exposure (route risk off) and say so |
| Exposure back-test disappoints | Tune YAML weights, report honestly; the story still stands as "risk indicator" |
| Time overrun | Follow the cut order in §10; M1–M8 and the test gate are protected |
| SQLite lock under parallel requests | WAL mode; idempotent auto-run; tested in suite F |
| C: drive fills up | Phase 0 redirects + audit script; run it again after Phases 4, 12, 14 |

---

## Appendix A — `.env.example`

```
APP_ENV=dev
DATABASE_URL=sqlite:///E:/Projects/factory-continuity-desk/backend/data/fcd.sqlite
CORS_ORIGINS=http://localhost:5173

# Weather: live | replay | synthetic  (replay = safe demo mode)
WEATHER_MODE=replay
REPLAY_EVENT=michaung_2023

# Drawing reading (free tier only; no billing)
GEMINI_API_KEY=
GEMINI_MODEL=            # fill after checking AI Studio free-tier models in Phase 0
VISION_PROVIDER_CHAIN=cache,gemini
OLLAMA_BASE_URL=http://localhost:11434   # optional
OLLAMA_MODEL=                            # optional

STALENESS_DAYS=90
```

Frontend `.env`: `VITE_API_URL=http://localhost:8000/api/v1`

## Appendix B — Everyday commands (PowerShell, from `E:\Projects\factory-continuity-desk`)

```powershell
# backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
.\.venv\Scripts\python.exe scripts\reset_demo.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
# frontend
cd ..\frontend
npm run dev
```

## Appendix C — Plain-language wording for UI and pitch

| Say | Don't say |
|---|---|
| "Reads your drawing and fills the passport; you confirm it" | "AI-powered extraction" |
| "Where your factory breaks" | "Intelligent risk analytics" |
| "Checked against the partner's declared profile" / "Unverified" | "Verified match" (unless the checks are actually done) |
| "Risk indicator from forecast rain and site conditions" | "Flood prediction" |
| "Reconfirm needed" | "Expired AI score" |
| "Sample / simulated" | (omit the label) |

## Appendix D — `docs/PROGRESS.md` template

```
- [ ] Phase 0  Environment & E: drive
- [ ] Phase 1  Backend skeleton
- [ ] Phase 2  Data model & catalogues
- [ ] Phase 3  Demo world & seeding
- [ ] Phase 4  Real-data prefetch
- [ ] Phase 5  M1 API
- [ ] Phase 6  M3 SPOF
- [ ] Phase 7  M4 Exposure
- [ ] Phase 8  M5 Stress test
- [ ] Phase 9  M6 Matching
- [ ] Phase 10 M8 Readiness
- [ ] Phase 11 M7/M9/M10
- [ ] Phase 12 M2 Passport + RFQ
- [ ] Phase 13 Orchestration
- [ ] Phase 14 BACKEND TEST GATE
- [ ] Phase 15 Frontend setup
- [ ] Phase 16 Frontend screens
- [ ] Phase 17 Integration test
- [ ] Phase 18 Freeze & submission
```

## Appendix E — Quick resume index

- **Phases 0–4:** setup, skeleton, data model, demo world, real-data cache. No analytics yet.
- **Phases 5–11:** the deterministic spine (M1, M3, M4, M5, M6, M8, M7 + mocks).
- **Phase 12:** the single drawing-reading module (M2) and redacted RFQ.
- **Phase 13:** orchestration; **last backend phase**.
- **Phase 14:** the backend test gate.
- **Phases 15–17:** basic frontend and integration.
- **Phase 18:** freeze and submission.
