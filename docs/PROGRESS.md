# PROGRESS

Phase tracker. Updated at the end of every phase (R11).

## Phases

- [x] Phase 0  Environment & E: drive
- [x] Phase 1  Backend skeleton
- [x] Phase 2  Data model & catalogues
- [x] Phase 3  Demo world & seeding
- [x] Phase 4  Real-data prefetch
- [x] Phase 5  M1 API
- [x] Phase 6  M3 SPOF
- [x] Phase 7  M4 Exposure
- [x] Phase 8  M5 Stress test
- [x] Phase 9  M6 Matching
- [x] Phase 10 M8 Readiness
- [x] Phase 11 M7/M9/M10
- [x] Phase 12 M2 Passport + RFQ
- [x] Phase 13 Orchestration
- [x] Phase 14 BACKEND TEST GATE (required suites and C: audit passed; `backend-v1` tagged)
- [x] Phase 15 Frontend setup (delivered as F0–F2)
- [x] Phase 16 Frontend screens (delivered as F3–F9; F10 backdrop is an optional stretch)
- [x] Phase 17 Integration test (replay UI/API path and failure fallback verified)
- [x] Phase 18 Freeze & submission (checks passed on the demo machine; `v1.0` tagged)

## Frontend planner subphases

Phase 14 was initially deferred by user choice. The user later authorized it; suites A–K and M passed and `backend-v1` was tagged on 2026-11-15. Snapshot capture and Phase 17 replay integration are complete; F11 performance/accessibility/rehearsal and Phase 18 freeze remain pending.

- [x] F0 Foundations
- [x] F1 Component library
- [x] F2 App shell, navigation, shutter
- [x] F3 Desk
- [x] F3 Exposure
- [x] F4 Weak Points
- [x] F4 What-if
- [x] F5 Recovery
- [x] F5 Partners & Readiness
- [x] F6 Passports & RFQ
- [x] F7 Stage Controls, Presenter, Proof, System (snapshot fallback captured and wired)
- [x] F8 Landing hero (visual review approved; full-tier performance confirmed smooth)
- [x] F9 Landing scroll story (visual review approved; smoother scroll verified)
- [ ] F10 Persistent world backdrop (optional stretch, deliberately cut)
- [x] F11 Integration, performance, rehearsal, freeze (machine checks passed; `v1.0` tagged)

## Required-first completion plan (user direction 2026-11-15)

1. **Phase 14 closeout — DONE:** suites A–K and M passed; `docs/TEST_REPORT.md` and `docs/openapi.snapshot.json` committed/pushed; `backend-v1` tagged. Optional suite L was not run.
2. **F9 Landing scroll story — DONE:** visual review approved; smoothing, checks, commit and push complete.
3. **Snapshot safety net — DONE:** captured the isolated replay pack and wired the offline System action, global saved-snapshot ribbon, and read-only API/UI mode.
4. **Phase 17 integration — DONE:** live replay UI/API flow, presenter routing, recovery handoff, readiness uplift and failure fallback verified; details below. External live-provider mode was not exercised.
5. **Phase 18 freeze/submission:** performance and accessibility pass, rehearsal, final screenshots and submission freeze.

After those required items, handle remaining optional work: F10 persistent world backdrop (stretch/cuttable), optional live provider smoke (L), and a captured hero poster if useful. F8's 50+ fps target is measured in the required F11 performance pass.

## Decisions and deviations from the blueprint

Recorded here so the blueprint stays pristine and both files remain readable to a future session.

| # | Blueprint says | What we did | Why |
|---|---|---|---|
| D10 | Frontend Planner FR2: Phase 14 backend gate passes and `backend-v1` is tagged before F0 | The frontend proceeded against the existing API contract while Phase 14 was deferred; the user later authorized it, and the gate passed | The user initially chose to build frontend screens first, then explicitly reauthorized the backend gate |
| D11 | Phase 14 / `backend-v1` | Suites A–K and M passed on 2026-11-15; optional live suite L was not run. Tag `backend-v1` points at the Phase 14 completion commit | Phase 14 was explicitly reauthorized by the user; see `docs/TEST_REPORT.md` |
| D1 | Root at `E:\Projects\factory-continuity-desk\` | Root at `E:\VihaanX-Build\` | User decision at kickoff. `.env.example` `DATABASE_URL` rewritten to match. No other path assumptions in code (all paths resolved via `pathlib`) |
| D2 | Python 3.12 installed to `E:\Python312` | Kept existing `C:\Users\Aadil\AppData\Local\Programs\Python\Python312` (3.12.10) | Reinstalling the interpreter mid-event adds risk with no real gain: the bulk (venv + site-packages) is on E:, which is what the C: rule is protecting |
| D3 | Ollama optional, models on `E:\dev-cache\ollama` | Ollama dropped | E: has 13.3 GB free; a vision model would consume most of the remaining headroom. Provider chain runs cache -> Gemini -> text rules -> manual |
| D4 | GitHub repo `factory-continuity-desk` created in Phase 0 | Remote is `https://github.com/aadil-naseem/project-relay` (user pre-created it empty, per the organisers' submission rule) | Repo name on GitHub is `project-relay`, matching the renamed project. `origin/main` now tracks `main` |
| D5 | `npm_config_cache` / `npm_config_prefix` user env vars | Also written to `C:\Users\Aadil\.npmrc` | npm reads `.npmrc`, not the inherited env block, so the env vars alone left npm pointed at `C:\Users\Aadil\AppData\Local\npm-cache` |
| D6 | Install `requirements-data.txt` (OSMnx) in Phase 0 | Deferred to Phase 4 | Connection is running ~80 kB/s; OSMnx pulls geopandas/pyproj/fiona/scikit-learn (hundreds of MB). It is only needed for the one-time prefetch. If it still fails, the cut order allows site-only exposure |
| D7 | - | `check_c_drive_leaks.ps1` rewritten to resolve process -> user -> machine | Windows does not push updated user env into an already-running shell, so a naive `$env:` check reports false leaks. Script now distinguishes STALE-PROCESS from LEAK |
| D8 | `PIP_CACHE_DIR` user env var | Also written to `C:\Users\Aadil\AppData\Roaming\pip\pip.ini` | Same reason as D5: a shell without the env var makes pip fall back to `C:\Users\Aadil\AppData\Local\pip\cache`. **The file must be UTF-8 without BOM** - with a BOM, pip silently outputs nothing and exits 0 |
| D9 | - | Deleted the pre-existing `C:\...\Local\npm-cache` (5.10 GB) and `C:\...\Local\pip` (0.75 GB) | C: had **0.00 GB free**. After cleanup: **6.36 GB free**. These were caches from before the redirect, not project data |

## Open questions carried forward

- `docs/03_FRONTEND_PLAN.md` was never supplied. Phases 15-17 therefore build the **basic** UI only; the 3D scroll landing remains unplanned.
- Zone membership source of truth pinned in Phase 2: `factories.hazard_zone_id` (and vendors/suppliers alike) is authoritative; `site_terrain.zone_ids` is derived at prefetch time only.

## Phase log

### Phase 0 - DONE
- E: folder layout created; caches and TEMP redirected to `E:\dev-cache`.
- Tools verified: Node 24.16 on E:, Git on E:, Python 3.12.10 on C: (see D2).
- Backend venv on E: with all runtime + dev packages. Versions: fastapi 0.162.7, pydantic 2.14.3, sqlalchemy 2.1.8, numpy 2.5.4, shapely 2.2.0, pymupdf 2.1. All imports verified.
- Frontend scaffolded with Vite (React 19.3.1, three 0.187, R3F 9.8.2); libraries installed, 0 vulnerabilities; `npm run build` passes (177 ms).
- Repo tree (section 5) created with stubs; brief and blueprint copied into `docs/`.
- Git initialised on `main`, first commit `64ceddf`, 134 tracked files; `node_modules`, `.venv`, `.env` confirmed ignored.
- C: leak audit passes: pip/npm cache, prefix, TEMP, TMP, HF_HOME, Playwright all resolve to E:. Project footprint 599 MB; E: free 11.9 GB.
- **Open-Meteo verified live** (see VERIFIED_FACTS.md). Two findings that change the plan:
  1. Live forecast for Ambattur right now is **dry (1.1 mm / 72 h)** - so `live` mode produces no alert. Replay is mandatory for the demo, not optional.
  2. Michaung archive is strong: **238.7 mm on 2023-12-04**. Replay series should start **2023-12-03T00:00Z** so onset lands at ~37-40 h rather than ~72 h.
- **Gemini verified live**: `gemini-3.5-flash-lite` is the only responsive model on this key. Text 1.5 s, vision 5.6-13.1 s (variable). Larger flash models are 404/503/timeout. Golden cache is therefore load-bearing, not optional.
- Outstanding, deliberately deferred: `requirements-data.txt` (OSMnx, D6) and the GitHub remote (D4).

**Phase 0 done-when checklist:** python + node work from E: (PATH) - **PASS**; installs produced no C: leak - **PASS**; repo pushed to GitHub - **PASS** (remote `project-relay` added retroactively at kickoff of Phase 2; empty repo was pre-created by the user per organisers' rule); `.env` has Gemini key - **PASS**; smoke results recorded - **PASS**; folder tree matches section 5 - **PASS**.

### Phase 1 - DONE (commit 2615245)
- `settings.py`: pydantic-settings reading `backend/.env` resolved from the file location, not CWD; env vars beat .env (pytest depends on this).
- `db.py`: engine + WAL + FK pragma + `Base` (tables land in Phase 2) + `get_db` dependency + `init_db()`.
- `core/clock.py`: UTC-aware `now()` with `set_now` / `reset_now` / `frozen_time` for deterministic tests.
- `core/geo.py`: haversine + point-in-circle.
- `core/trace.py`: JSON-safe calculation-log builder (recursive stringification).
- `errors.py`: `AppError` + handlers for AppError / validation (422) / HTTP (404) / unexpected (500), all through `{"error": {code, message, details}}`.
- `config_loader.py`: all 7 YAMLs load into typed pydantic models with fail-fast validators (weights sum to 1, breakpoints ascending, default window in windows list). Generic aliases validated via `TypeAdapter`.
- All 7 YAML constants written from section 7 + the demo world (section 9) + back-test sites; replay start 2023-12-03T00:00Z per Phase 0 verification.
- `api/health.py`: status + db + weather mode + vision chain (cache/gemini configured booleans).
- `pyproject.toml`: ruff (E4/E7/E9/F/I, line 120) + pytest config + `live` marker.
- Tests: 27 passing (health, clock, geo, trace, errors, config loader). Test DB on E:, disposed before deletion (Windows file-lock lesson).
- Done-when: uvicorn serves `/docs` (200) and `/api/v1/health` (status ok, db ok, weather_mode replay, both vision providers configured); pytest green; ruff clean.

**Lessons recorded for later phases:** YAML parses unquoted ISO timestamps as datetime (model now typed `datetime`) and unquoted commas inside flow mappings split keys (quote strings with commas). Numeric-looking material aliases must be quoted.

### Phase 2 - DONE (commit 633f6d4, pushed)
- `enums.py` per section 6 plus extras the data model needs: Trigger, VendorKind, PassportStatus, ShareLevel. `RiskLevel.from_score` carries the bands (LOW < 25, MODERATE < 50, HIGH < 75, SEVERE >= 75).
- All 22 ORM tables in `app/models/`: factory aggregate (factories, machines, vendors, vendor_links), parts spine (parts, part_steps, orders), passports (passports, rfqs, passport_shares), relationships (backup_relationships, relationship_checks), hazard facts (hazard_zones, site_terrain, routes), computed stores (forecast_cache, exposure_snapshots, stress_tests, readiness_snapshots), recovery (recovery_requests, recovery_steps), app_state.
- `parts.passport_id <-> passports.part_id` cycle solved with `use_alter=True, ondelete="SET NULL"` on both sides; insert ordering consequence handled (passport committed before parts reference it).
- Pydantic schemas for every section 8 endpoint (shapes only; routers are Phase 5+). Uniform error envelope and TraceEntry in `schemas/common.py`.
- `scripts/init_db.py` (with sys.path bootstrap): builds all 22 tables against `backend/data/fcd.sqlite`, WAL verified.
- Tests: 46 passing (enum coverage, full write->read round trips through real schema, FK enforcement, table-set equality). Ruff clean. Server boots with models loaded.
- Done-when: `init_db.py` creates 22 tables; WAL on, foreign_keys on through the app engine; pytest green; ruff clean; `/api/v1/health` ok.

**Lessons recorded for later phases:** SQLite PRAGMAs are per-connection - the engine's connect listener sets them, so a raw `sqlite3.connect` shows foreign_keys=0 (not a bug). `use_alter` FKs are excluded from insert ordering, so seed/test code must commit the referenced row first. Scripts need `sys.path.insert(0, backend)` to import `app` when run as files.

### Phase 3 - DONE (commit d421634, pushed)
- Seed JSON per section 9 in `backend/data/seed/`: `factories.json` (owner + 6 partners, coordinates matching cluster.yaml), `vendors.json` (ven_heat + sup_steel, both inside the owner's flood zone), `machines.json` (32 machines: owner fleet 3 TURN / 2 MILL / 1 DRILL_TAP / 1 GRIND_CYL +-0.005 = the SPOF; partner fleets sized to the story), `parts.json` (6 parts, 12 steps, routes exactly per the table), `orders.json` (8 orders, `due_in_days`: three worth 2.47M INR due within 5 days behind the storm window), `relationships.json` (6 relationships + 30 checks).
- Relationship story per Phase 3 task 2: Oragadam READY fresh (~40 d, all checks), Hosur APPROVAL_PENDING missing exactly CUSTOMER_APPROVED + CAPACITY_RECONFIRMED, Peenya READY ~120 d (stale, > 90), Coimbatore POTENTIAL_MATCH (assessment found the tolerance gap, never confirmed), Ambattur neighbour + Guindy READY (exclusion, not status, is the reason they fail invariant 4).
- `app/demo_seed.py`: loader with fail-fast count validation; relative dates converted against the frozen clock; `seed()` wipes its own tables first (re-runnable, prefetch/runtime tables untouched); `reset_demo()` = drop + create + seed + initial readiness snapshot row (`rdy_initial`); `verify_counts()` for tests/scripts.
- `scripts/seed.py` (seed into existing schema) and `scripts/reset_demo.py` (one-command reset, checks the < 3 s done-when itself).
- Tests: 12 new (58 total): counts, is_sample everywhere, relative dates vs frozen clock, reset-twice identical full-table dump, initial snapshot, section 9 story shape, owner fleet, part routes, seed-files vs cluster.yaml consistency (factories + vendors cover every config site).
- Done-when: `reset_demo.py` runs in **0.09 s** (< 3 s budget) and produces all section 9 entities; ruff clean; server boots.

**Lessons recorded for later phases:** cluster.yaml `sites` includes the vendor and supplier, so "seed factories == config sites" is wrong - the union of factories.json and vendors.json must equal the site list. seed() wiping its own tables (not drop_all) keeps prefetch data safe once Phase 4 lands; `POST /demo/reset` (Phase 13) should call `reset_demo()` which drops everything.

### Phase 4 - DONE (commit 8f03adc, pushed)
- **OSMnx installed after all (D6 risk cleared):** osmnx 2.1.1 + geopandas 1.2.0 + pyproj 3.8.0 installed cleanly; scipy-free nearest-node lookup written by hand (vectorised numpy haversine over the 77k-node graph) to avoid the scikit-learn optional dependency.
- `prefetch_terrain.py` -> `data/cache/terrain.json`: 16 sites (9 demo + 7 back-test), centre + 3 rings (500/1000/2000 m) x 8 bearings via the Open-Meteo elevation API (batch 100 VERIFIED live); owner -4.7 m below ring mean (depression), Oragadam 53 m plateau; 15x15 cluster grid -> `low_threshold_m` 13.0 m.
- `prefetch_routes.py` -> `data/cache/routes.json`: Chennai drive graph downloaded once (77,285 nodes, cached in git-ignored `data/raw/graph_chennai.graphml`); 14 routes (4 Ambattur sites x 3 exits + Guindy x 2), 3.6-13.1 km, sampled every 250 m, 488 sample elevations batched, low_share + underpass counts (tunnel/layer<0). Scope decision: routes only for storm-footprint sites; far partners keep null route facts (schema supports; M4 degrades to site-only). Nearest-water distances filled for all 9 demo sites (Overpass 502 retries needed; fac_owner 169.4 m - Ambattur lake vicinity).
- `prefetch_replay.py` -> `replay_michaung.json` (16 sites x 72 h from 2023-12-03T00:00Z; owner 2023-12-04 total **238.7 mm, matches the Phase 0 reference exactly**; flooded back-test sites 225-315 mm; Hosur 0.4 / Peenya 2.5 / Coimbatore 1.7 mm - dry inland, supports the matching story) + `synthetic_storm.json` (labelled SYNTHETIC SAMPLE, deterministic ramp, last-resort mode).
- `data/cache/zones.json`: 5 curated circles with real citations (KNN India, The Hindu, The Week, Deccan Herald, Businessline) recorded in VERIFIED_FACTS.md; labelled "illustrative planning zones... NOT official flood maps".
- Seeder: `load_exposure_cache()` in `app/demo_seed.py` loads zones/terrain/routes into the DB during `reset_demo()` (zone membership derived with the circle test into `site_terrain.zone_ids`; factory membership stays on `factories.hazard_zone_id`). `nearest_water_m` made nullable in the model.
- Tests: 16 new (74 total), all offline. Done-when: cache committed (152 KB JSON total), reset in 0.32 s with everything loaded; no network in tests.

**Lessons recorded for later phases:** Overpass-api.de 502s under load - retry with backoff (water lookups are the flaky part; routes + elevations are stable). OSMnx drops its HTTP cache into `./cache` relative to CWD (now git-ignored as `backend/cache/`). osmnx `nearest_nodes` on an unprojected graph needs scikit-learn - hand-rolled haversine argmin avoids it. OSMnx keeps `tunnel` but not `layer` by default - append `layer` to `useful_tags_way` before downloading.

### Phase 5 - DONE (commit 95212bc, pushed)
- `core/status_rules.py` (pure): `required_checks_for` per the 7.5 table (APPROVAL_PENDING needs TECH only; READY needs TECH+SAMPLE+TERMS+CAPACITY + CUSTOMER when required; UNAVAILABLE_EXPIRED from any state), `missing_checks_for`, `effective_status` (READY past staleness reads STALE, never stored), `is_expiring_soon` for the Phase 10 review.
- `services/factories.py`: CRUD with UUID4 runtime ids; `create_machines` honours `count=N` -> N rows (section 7.1); order creation validates part existence (404) and factory ownership (409 PART_NOT_IN_FACTORY).
- `services/relationships.py`: effective status computed at read time from readiness.yaml `staleness_days`; `patch_status` guard raises 409 MISSING_CHECKS with `details.missing_checks`; `complete_check` (CAPACITY_RECONFIRMED refreshes last_confirmed_at) and `reconfirm`.
- Routers `api/factories.py` + `api/relationships.py` wired into main: GET/POST /factories, GET/PUT /factories/{id}, POST /factories/{id}/machines (list response), PUT/DELETE /machines/{id}, GET /factories/{id}/parts, GET/POST /factories/{id}/orders (part_id filter), GET /factories/{id}/relationships, PATCH /relationships/{id}/status, POST /relationships/{id}/checks/{key}/complete, POST /relationships/{id}/reconfirm.
- Tests: 15 new API tests (89 total) in tests/api/test_m1_api.py: CRUD round trips, count=N, error envelope shapes (422/404/409), guarded transitions (Hosur blocked with exactly the two missing checks; Cbe -> APPROVAL_PENDING legal; UNAVAILABLE_EXPIRED from any state), complete-checks-then-READY, reconfirm cures staleness (Peenya STALE -> READY), orders part filter.
- Done-when verified live: server boot with seeded DB, /health ok, peenya status READY effective STALE, hosur APPROVAL_PENDING; ruff clean.

**Lessons recorded for later phases:** a required Pydantic field that is computed (effective_status) needs a schema default so the ORM row validates, then the service overwrites it at read time. PUT endpoints need a separate all-optional Update schema (MachineCreate with required fields 422s on partial updates). The conftest `client` fixture now freezes the clock too, so API tests are deterministic end to end.

### Phase 6 - DONE (commit 5588e83, pushed)
- `core/spof.py` (pure, no DB/FastAPI): `Resource` (machine/vendor/supplier view), `StepRequirement`, `OrderRequirement`, `find_spofs()` implementing the section 7.1 coverage algorithm exactly - requirements = every step + the material, `servers(req)` with the machine process/tolerance/envelope filters, remove-one-resource-and-recheck, rank by revenue desc then order count then id. Returns ranked items, part/step/resource graph nodes+edges, `uncovered_requirements`, `excluded_resources`.
- Two modelling decisions **recorded**: (1) requirements with zero servers at baseline are reported in `uncovered_requirements` and are not blamed on any resource - otherwise every resource would "break" a part with no approved supplier; (2) `outsourced` routes a step to approved vendors, in-house steps to own machines (documented in the module docstring).
- `services/spof.py`: builds the world from the DB (own machines, linked vendors/suppliers, orders + part routes, passport envelope when present), computes the static exposed flag (hazard zone on the site row or `site_terrain.zone_ids`; live exposure joins in Phase 13), and emits a trace (load_world, coverage, remove_resource per SPOF, rank).
- `api/spof.py`: `GET /factories/{id}/spof` (409 NOT_AN_OWNER for a partner, 404 NOT_FOUND for unknown); schema extended with `uncovered_requirements` + `total_orders`; node kinds widened to part/step/machine/vendor/supplier.
- Tests: 21 new (110 total). Unit: three lathes never a SPOF, lone grinder is, ranking tie-breaks, tolerance filter, envelope filter, unavailable machine excluded, outsourced routing, supplier material match, exposed flag, graph shape, empty world. **Hypothesis property test (200 examples)** cross-checks the algorithm against an independent brute-force remove-and-recheck implementation.
- Done-when verified against the seeded world: top SPOF is `ven_heat` (₹19 L, ord_101+ord_106), then `mch_own_grind_1` (₹12 L) and `sup_steel` (₹12 L), all `exposed=true`; the three lathes and both VMCs never appear. Section 9 invariant 3 holds.

**Lessons recorded for later phases:** a single supplier is itself a SPOF - test fixtures that want "material is not the point" need two suppliers of the same grade. Uncovered requirements are a normal state in the demo world (only EN24 has an approved supplier), so later modules must not assume full material coverage. The hypothesis strategy must collapse duplicate ids, since generated ids can repeat.

### Phase 7 - DONE (commit bbf7589, pushed)
- `adapters/weather.py`: `get_hourly_precip(session, sites, mode)` with the full section 3.4 ladder. **live** = one batched Open-Meteo call (multi-location returns an array - verified live), sliced from the current UTC hour over a 4-day request; good responses are written to `forecast_cache`. **cache** on live failure; **replay** (real Michaung series, index 0 = now) as the last fallback; **synthetic** reads the labelled generated profile. Every result carries `source` and `degraded`.
- `core/exposure_score.py` (pure): rolling sums, `piecewise`, `rain_hazard` (H = max of 24 h and 3 h bands), `vulnerability` (depression/water/zone with clamps), `site_risk`, `route_risk` (`V_route`), `is_isolated`, `onset_and_wet_spell`, `alert_affected`, `explain_drivers`. Honest nulls throughout: unknown water distance = no evidence, missing route facts = `route_risk: null`.
- `services/exposure.py`: TTL cache (`cache_ttl_minutes`) around the *weather fetch* only (arithmetic is cheap and always recomputed so a demo reset cannot be masked), writes an `exposure_snapshots` row per computation keyed by a 32-char forecast hash, resolves mode as `?mode=` > `app_state` > `.env`, and emits a full trace (weather, per-site arithmetic, routes, alert).
- Routers: `GET /factories/{id}/exposure?mode=`, `GET /exposure/map`, `POST /demo/mode`, `GET /demo/state`.
- Tests: 38 new (148 total) - pure-function maths with hand-computed numbers (148 mm -> 0.873), route risk with/without underpasses, isolation edge cases, onset/spell, alert threshold edges (49 vs 50), and respx-mocked live/cache/replay/synthetic ladder including malformed payloads and HTTP 503.
- **Tuned one config constant** (`heavy_onset_mm_3h: 5 -> 10`, recorded in VERIFIED_FACTS): at 5 mm/3 h the Dec-3 drizzle tripped onset at hour 0; 10 mm/3 h is the IMD "heavy" 24 h rate expressed per 3 h and puts onset at h23.
- Back-test written to `docs/BACKTEST_EXPOSURE.md`: **PASS with +12 points separation** (flooded 70-82, not flooded 29-58). Real OSM water distances for the back-test sites were added after the first run and *increased* separation, so the result is not tuned to the labels.
- Done-when verified live: owner **98 SEVERE** with readable drivers (242 mm/24 h, 56 mm/3 h, 4.7 m depression, 169 m from water, in a planning zone), alert active (owner + heat vendor + supplier), onset 23 h, Oragadam 58 < Ambattur 96.

**Lessons recorded for later phases:** Oragadam scores 58 (HIGH) in the replay because the archive really did drop ~180 mm/24 h there - it is *less* exposed than Ambattur, not unexposed. Phase 9 must not use "risk >= alert_threshold" alone as the correlated-risk test or the hero backup would be excluded; use a relative test and document it. The TTL cache keys on (mode, site set) and must be cleared by `reset_weather_ttl()` after a demo reset, otherwise a stale live result can survive.

### Phase 8 - DONE (commit 090c030)
- `core/hazards.py` (pure): `resolve_affected_sites` (zone, cluster, grid, sites, exposure_alert, resource) and `build_downtime_windows` implementing the section 7.3 hazard-to-effects table (`FLOOD`, `POWER_OUTAGE`, `WATER_OUTAGE`, `ACCESS_BLOCKED`, `RESOURCE_DOWN`).
- `core/scheduler.py` (pure): deterministic list scheduler with EDD priority, pre-emptive resume `finish_time`, machine capability matching (process, tolerance, envelope), outsourced vendor handoff + 4h transport legs, supplier lead times, access-blocking delays, and baseline vs. stressed comparisons.
- `services/stress.py`: loads factory shop floor, linked vendors and suppliers, orders and parts; builds downtime windows; executes simulation; formats plain-language headlines; persists `stress_tests` rows; implements idempotent `run_auto_for_alert`.
- `api/stress.py` & `main.py`: `POST /api/v1/stress-tests` and `GET /api/v1/stress-tests/{id}` wired into `/api/v1`.
- Tests: 27 new tests across `test_finish_time.py`, `test_hazards.py`, `test_scheduler_core.py`, `test_stress_service.py`, and `test_scheduler_properties.py` (Hypothesis property tests for machine non-overlap, step sequence integrity, and monotonic delays).
- Section 9 story invariant 2 verified: auto stress test yields `orders_at_risk >= 2` (3 orders), `revenue_exposed_inr >= 1,000,000` (₹24.7 L), and `orders_no_fallback >= 1`.
- Done-when verified: manual FLOOD test produces LATE orders with sensible dates; auto test attaches to alert and is idempotent; property tests pass.

**Lessons recorded for later phases:** in parallel multi-machine list scheduling, Graham's anomaly can shift order assignments across machines; monotonic order delay strictly holds for dedicated routing or overall makespan. Phase 9 M6 matcher will wire into `services/stress.py` to replace the `FallbackLevel.NONE` stub with candidate searches.

### Phase 9 - DONE (commit aca978e, pushed)
- `core/matching.py` (pure): six hard filters (process/material/tolerance/envelope/capacity/lead_time) each returning PASS/FAIL/UNKNOWN with basis+detail (capacity UNKNOWN when the relationship is stale, per section 7.4); UNVERIFIED requirement list flipped to verified by completed relationship checks; correlated-risk exclusions (SAME_CLUSTER, SAME_HAZARD_ZONE, SAME_GRID only under POWER_OUTAGE else down-rank flag, ALSO_EXPOSED_SAME_EVENT, NEARBY down-rank); ranking `score = 100*(0.40*status_w + 0.20*time_slack + 0.15*capacity_slack + 0.15*freshness + 0.10*separation)` with STALE READY weighted 0.5 and flagged RECONFIRM_NEEDED; greedy top-2 set selection avoiding correlation among picks; `fallback_level` READY | POTENTIAL_ONLY | NONE.
- `services/matching.py`: loads candidates (partner machines, relationships, completed checks), resolves the scenario context (hazard, affected sites) and **always computes partner site risks fresh through the exposure service** in the current demo weather mode (idempotent snapshot writes keyed by forecast hash). Full trace.
- `api/matching.py`: `POST /matching/search {order_id, scenario?}`; the Phase 8 stub in `services/stress.py` now calls the real matcher so stress results carry real `fallback_level` + `best_backup`.
- Tests: 4 new files (filters, exclusions, ranking, service/API) - every filter pass/fail/unknown case, every exclusion reason, set selection avoiding correlated pairs, and the section 9 invariants: hero order PRT-B has exactly one viable READY (Oragadam) + one viable APPROVAL_PENDING (Hosur) + excluded correlated candidates; PRT-A fallback NONE.
- **Two documented changes to make invariant 4 hold honestly** (blueprint Phase 9 task 5 sanctions tuning; no site names in code or config):
  1. `config/exposure.yaml` `depression_full_m: 3.0 -> 5.0`. Oragadam dips exactly 3 m below its ring mean on the 53 m plateau; at 3.0 the depression term saturated (D=1.0) and its indicator hit 58, above the alert threshold, which would have excluded the hero backup. 5.0 matches the floodplain scale that actually flooded (owner -4.7 m at 14 m elevation). Effect verified: Oragadam 48 (below threshold, viable), Guindy 67 unchanged (excluded), owner 96 SEVERE (alert unchanged), and the Michaung back-test separation **improved from +12 to +22** (`docs/BACKTEST_EXPOSURE.md` regenerated).
  2. `services/matching.py` computes partner exposure fresh instead of silently falling back to `site_risk=None` when no snapshots exist yet (the hero-invariant test failed exactly this way after `reset_demo()`); without this the correlated-risk exclusion could never fire on a fresh database.
- Done-when verified live: `POST /matching/search` on ord_102 -> fallback READY, recommended set [fac_oragadam, fac_hosur], Guindy excluded ALSO_EXPOSED_SAME_EVENT, Ambattur neighbour excluded SAME_CLUSTER, Peenya STALE flagged; ord_101 -> fallback NONE. 191 tests passing, ruff clean.

### Phase 10 - DONE (commit d9c5125, pushed)
- `core/readiness.py` (pure): capability = material (grade or family via materials.yaml) + an available machine for every step (process/tolerance/envelope); static non-correlation per 7.5 (different cluster, zone AND grid, >= min_separation_km); coverage ladder with documented precedence NO_PARTNER_ELIGIBLE -> CORRELATED -> STALE -> NOT_READY -> NO_CAPACITY -> TOO_SLOW -> COVERED; capacity `qty*hpu+setup <= spare_hours_per_week[p] * W/168` per process; lead time `mobilisation + production + logistics` with production `= sum((batch_run/n_machines + setup) * 24/shift)` and logistics `= distance/35 + 4`; unweighted and revenue-weighted scores per window; coverage is monotone in W (tested); `review_partners` flags STALE and READY partners within `expiring_soon_days` of going stale.
- `services/readiness.py`: loads critical parts weighted by open-order value (fallback 1), writes one `readiness_snapshots` row per window on every call, builds the preparedness review, and computes **counterfactual next-best actions** (recompute with the relationship forced READY+fresh; uplift = real weighted-score delta at the headline window; zero-gain actions omitted; top 5 by gain). `record_snapshot` is also called on every relationship status change, check completion of CAPACITY_RECONFIRMED, and reconfirm (Phase 5 services), so transitions appear in history. History excludes the INITIAL row written by reset_demo.
- Routers: `GET /readiness/{id}?window=`, `/actions?window=`, `/history`; 409 NOT_AN_OWNER for partners, 422 for unknown windows. `ActionsOut` schema gained the trace list.
- Seed tuning (sanctioned by section 9 "tune the seed until invariants hold", documented): Oragadam gained a DRILL_TAP centre (the section 9 story table says PRT-C is covered by Oragadam - no partner owned a drill) and partner `spare_hours_per_week` were sized to their fleets (e.g. Oragadam 2 lathes -> TURN 120 h/wk). Machines 32 -> 33.
- Tests: 16 new (207 total): hand-computed 3-part example (66.7/50.0), stale exclusion + reconfirm raise, uncorrelated requirements (cluster/grid/distance), the full reason ladder, lead-time and capacity formula unit checks, review expiring flag, and the seeded-world invariants: **5** (Peenya STALE covers nothing; reconfirming it moves the score by exactly 0) and **6** (initial 48 h = 53.9 in [30,55]; after Hosur checks + READY the weighted score rises to 70.9, +17.0 >= 10; unweighted 50 -> 75).
- Done-when verified live: top action "Complete checks and set Sample Engineering (Hosur) READY -> +17.0 (to 70.9)"; executing it produced **exactly 70.9** - predicted uplift equals the real delta. History recorded 12 snapshot points across the demo actions.

### Phase 11 - DONE (commit 6a392fa, pushed)
- `services/recovery.py`: `create_request` accepts `{from_stress_test_id, order_id}` (prefill: factory from the stress test, order must belong to it and to the stress result) or `{factory_id, order_id}` (manual); creates the 7 tracking rows (PENDING) at creation; passport_id attached from the part when one exists. `request_out` runs the M6 matcher with the originating stress test's scenario (hazard + affected sites) so options carry true exclusion reasons, plus per-option outstanding checks ("CUSTOMER_APPROVED pending", or the staleness reconfirmation note) and a declared-capacity summary.
- `select_partner`: excluded -> 409 EXCLUDED_PARTNER (with reason), hard-filter FAIL -> 409 NOT_CAPABLE (with failed filter keys), switching after a selection -> 409 ALREADY_SELECTED, same partner idempotent 200. Selection marks REQUEST_SENT DONE and status ACTIVE. Every response states: "activation is subject to human, customer and contractual approvals outside the software".
- M9 handover: data-driven pack rendered through a Jinja2 template (`app/templates/handover.md.j2`) into `text` alongside the structured fields: job requirements (material, route with tolerances, tightest tolerance, outsourced notes), authorised documents, quantity/deadline, inspection checklist (MTC + first-article + tightest tolerance), responsibilities, required approvals, simulated milestones. **Consent-aware**: with FULL passport share the pack releases the passport, drawing number and part name; otherwise it is redacted (generic job label, no customer/drawing/part identifiers).
- M10 stepper: fixed order REQUEST_SENT -> PARTNER_RESPONSE -> TECHNICAL_AND_CUSTOMER_APPROVALS -> PRODUCTION_SCHEDULED -> PRODUCTION_STARTED -> QUALITY_INSPECTION -> DISPATCH_AND_DELIVERY; `tracking/advance` moves exactly one step (409 NO_PARTNER_SELECTED before selection, 409 ALL_STEPS_DONE at the end); everything labelled SIMULATED SAMPLE. `RecoveryRequest.steps` relationship added to the model (cascade delete-orphan).
- Routers: POST/GET /recovery-requests, GET /{id}, POST /{id}/select-partner, GET /{id}/handover, GET+POST /{id}/tracking(/advance).
- Tests: 10 new (217 total): prefill correctness incl. per-option outstanding checks; validation errors (422/404/409 ORDER_NOT_IN_FACTORY); excluded-partner 409 with exact reason; incapable-partner 409 (Hosur on PRT-A); stepper order + idempotent/guarded selection; handover redaction without consent (drawing number, part name, customer alias all absent); FULL-consent pack releases passport + drawing; handover/advance require selection.
- Done-when verified live (section 9 demo steps 5-6): prefill from a FLOOD stress test -> 6 options in story shape -> selecting the Ambattur neighbour 409s -> selecting Oragadam -> handover pack (qty 200, SIMULATED SAMPLE) -> 3 advances walk REQUEST_SENT -> PARTNER_RESPONSE -> TECHNICAL_AND_CUSTOMER_APPROVALS -> PRODUCTION_SCHEDULED.

### Frontend F0 - DONE (commit 9001df9, pushed)
- Copied the user-provided frontend planner to `docs/03_FRONTEND_PLANNER.md` as the repository reference.
- Installed verified npm packages: Zustand, Lenis, Big Shoulders Display, Instrument Serif, IBM Plex Sans, IBM Plex Mono. Fonts are imported from self-hosted Fontsource Latin subsets for offline use and smaller output.
- Added locked palette/design tokens, base reset/blueprint grid/focus ring, type/motion/layout variables, and the initial Foundation route shell with SAMPLE / SIMULATED title block.
- Wired React Router placeholders for all planner routes; added TanStack Query client, fetch client with 8 s timeout and normalized backend error envelope, and live health hook/chip. Backend `/api/v1/health` returned 200 in browser; every route placeholder loaded.
- Added `npm run lint:palette`; passed. `npm run lint` passed. `npm run build` passed. Initial JS bundle is 347.69 KB / 109.15 KB gzip, below the planner's 350 KB gzip budget; Three/R3F is not loaded in this initial shell.
- Browser console had no errors. Screenshot: `docs/screens/F0/desk-foundation.png`.
- F0 is infrastructure/placeholders only: no functional screen has been designed yet. Next up is F1 shared primitives, then F2 shell; after that implement one screen at a time and wait for user confirmation between screens.

### Frontend F1 - DONE (commit fc1d237, pushed)
- Added shared primitives under `src/components/primitives/`: Frame with registration ticks, Button variants/loading/disabled, Segmented, Chip, Nameplate, Stamp, Tooltip, Drawer, Dialog, Tabs, Toggle, Slider, Field/Input, striped Table, Skeleton, Toast, Kbd, and an inline glyph set.
- Added domain components under `src/components/domain/`: Risk/Order/Fallback/Backup status pills (shape + text + semantic palette, including STALE and EXCLUDED reason hatch), ConfidenceBars, DataLabelBadge, WeatherSourceBadge, Money, Odometer, StackLight, ShiftClock, HorizonBar, ReadinessRing, AlertBanner, DimensionLine, CalcLog, PaperSheet, RelayCircuit, ShiftChart, DependencyGraph, CandidateCard, RouteCard, RedactionSheet.
- Added centralized `src/lib/status.js` and `format.js`; all 4 risk levels / 3 order states / 3 fallback levels / 6 backup effective statuses / 5 confidence states are mapped.
- Added hidden `/app/_kit` visual-regression gallery; no product screen design was started. Browser accessibility snapshot showed all gallery sections and no console errors.
- Unit tests use Node's built-in runner: money and odometer formatting, distinct risk/status encodings, full backup statuses, and confidence bars: **6/6 pass**.
- Done gates: `npm test` PASS; `npm run lint` PASS; `npm run lint:palette` PASS; `npm run build` PASS (F1 bundle 363.59 KB / 113.88 KB gzip, below the 350 KB gzip budget; Three/R3F is still not loaded). Browser screenshot capture was unavailable during this phase; visual verification used the in-browser accessibility snapshot.

### Frontend F2 - DONE (commit 00a586b, pushed)
- Added the shared app shell: 72 px expandable/pinnable left rail, status strip (RELAY, sample factory, IST clock, sample stamp, source badge, health chip, stack light, Stage button), detail breadcrumbs, and mobile bottom navigation. Every app route and hotkey `1–8` maps to the planner's nav order.
- Added `useRelayNavigate` behavior in the shell: chevron shutter close/swap/open (240/320 ms); reduced-motion switches navigation to an immediate transition. Rail and screen changes leave page content as placeholders.
- Added command palette on `/` or Ctrl/Cmd+K with route navigation, Stage Controls entry, and Reset demo action; Escape closes. The Stage drawer remains intentionally a placeholder until F7.
- F2 browser smoke: shell and health status render, backend health request 200, command palette opens, hotkey `2` navigates to Weak Points, no console errors. All F0 API/test/lint gates remain green.
- F2 screenshot capture was attempted but the browser tool reported the tab was not visible; no screenshot is claimed for this phase.

### Frontend F3-S1 Desk - DONE (commit f7d0010, pushed)
- Replaced the S1 `/app` placeholder with the live Desk: alert banner and Start Recovery / See Test actions, 24/48/72 readiness ring + breakdown drawer, KPI odometers, top-3 SPOFs, rain dimension-line fallback, calc-log drawer, next-best actions, and Leaflet mini-map with risk-coded site markers and route-risk summaries.
- Data comes from the live dashboard, readiness, actions, exposure, exposure-map, and stress-test endpoints via TanStack Query. The primary CTA selects the highest-value at-risk order from the auto stress result, creates the recovery request, then navigates through the shutter.
- Honest API gaps handled explicitly: hourly rain samples are unavailable, so the Desk shows max-24h and onset callouts rather than invented bars; route geometry and zone geometry are not in the current map response, so the mini-map shows site markers and route risk summaries and states that route geometry is unavailable. OSM tile errors retain markers and report tile degradation.
- Browser verification against replay data: SEVERE owner alert at T+23 h, readiness 50 / weighted 53.9, KPIs ₹39.5 L / 6 at-risk / 2 no-fallback / 1 stale, heat vendor → grinder → EN24 supplier SPOFs, Hosur +17 point action, map and routes shown; no browser console errors. Clicked Start recovery request: it created a request for the highest-value at-risk order (`ord_101`) and navigated to the recovery detail placeholder. Demo reset performed after the smoke run.
- F3 Desk gates: `npm test` 6/6, `npm run lint`, `npm run lint:palette`, `npm run build` passed. Leaflet is lazy-loaded as its own chunk.
- Screenshot capture was attempted; the browser tool reported the tab was not visible. No screenshot is claimed for this subphase.
- **F3 Exposure - DONE** (commit 286cdb0, pushed; user reviewed the refreshed screenshot in chat).
- Exposure uses the live `/exposure/map` and owner exposure endpoints, ranks site markers, displays owner drivers and route risks, and overlays the real Phase 4 curated zones and three owner routes from a frontend copy of the committed prefetch cache (`src/data/exposureGeometry.json`). Zones remain labelled illustrative, not official flood maps.
- The 72-hour scrubber is intentionally hidden because `hourly_mm` is absent from the current API; selected-site panel shows max-24-hour rain and onset when available. Non-owner driver details are not fabricated; the UI states the map contract only supplies site risk.
- Browser smoke: owner 96 SEVERE with five actual drivers; Oragadam 48 MODERATE; selecting Oragadam updates the selected-site panel. Open-Meteo and OSM attributions visible; no console errors.
- `npm test` 6/6, `npm run lint`, `npm run lint:palette`, `npm run build` all pass. Leaflet map code is lazy-loaded.
- Visual review found the overlays had been too small at the initial all-site map extent. The initial viewport now focuses on the Chennai storm footprint while the ranked list keeps all sites; selecting a distant site pans to it. User-reviewed screenshot confirms the 5 curated zones and 3 owner routes are now visible.
- Browser screenshot tool could not save a local artifact (`tab not visible`); the user-provided screenshot was reviewed in chat and is not stored under docs/screens. Do not start F4 until user confirmation.

### Frontend F4-S2 Weak Points - DONE (commit 73a8d08, pushed; screenshot review pending)
- Replaced the S2 placeholder with the ranked SPOF list and SVG dependency drawing: active orders → parts → process steps → machines/vendors/suppliers. Order→part edges are joined from the orders endpoint; the remaining links come from the SPOF graph response.
- Selecting a weak-point row updates its details. **Simulate loss / Pull the plug** uses the backend `orders_broken` result to dim other resources, retract selected-resource edges, and hatch broken orders; Reset restores the graph. “Stress this resource” deep-links to What-if with `hazard=RESOURCE_DOWN&resource_id=...`.
- Shows exposure markers, affected-order nameplates, revenue at risk, calc log, uncovered requirements separately, and the note that three lathes never appear because two remain.
- Browser smoke against the live backend: ranks heat vendor ₹19 L, grinder ₹12 L, EN24 supplier ₹12 L, drill/tap ₹9.5 L; Pull the plug on the vendor highlights ord_101 + ord_106; What-if link carries `RESOURCE_DOWN&resource_id=ven_heat`. No console errors.
- `npm test` 6/6; lint, palette lint, and production build pass. User reviewed the uploaded Weak Points screenshot in chat; the browser screenshot tool could not save a local artifact. Hold before What-if until user confirmation.

### Frontend F4-S5 What-if - DONE (commit 0477781, pushed; user screenshot reviewed)
- Replaced the S5 placeholder with the disruption form: all five hazards, zone/cluster/grid/site/current-alert/resource scopes, curated-zone map picker, start-in and duration controls. Scope options use the committed seed/config views and live exposure/SPOF responses.
- Result view renders stress headline, at-risk/revenue/no-fallback metrics, SVG shift chart with baseline and stressed finish bars, due flags and hatched downtime band, and order rows with state/fallback/best-backup plus Open Recovery.
- `/app/what-if/:id` loads an existing stress test as **AUTO TEST · READ ONLY** with no Run button; the Desk and Weak Points deep links retain their IDs/parameters. Recovery actions prefill the matching order from the source stress test.
- Browser smoke: `RESOURCE_DOWN` deep link populated the selected grinder and returned a 1-order/₹12 L/no-fallback result; manual FLOOD zone run returned 4 at-risk orders/₹30.7 L and rendered due/fallback rows; auto test opened read-only; Open Recovery created a prefilled recovery request. Demo reset performed afterwards. No console errors.
- Gates: `npm test` 6/6; lint, palette lint, build pass. Map/scope zones are explicitly labelled illustrative. Rain samples/hourly scrubber unavailable by API contract; what-if visualization is based on actual baseline/stressed finish timestamps.
- User screenshot review: layout and chart are clear. Follow-up adds an explicit `+Nh` overflow marker when stressed completion extends beyond T+168 h (e.g. 172 h no longer visually clips at the chart edge). Browser screenshot tool cannot save the uploaded chat image locally.
- F5 Recovery is implemented and reviewed; Partners & Readiness is the current screen, with no further screen started.

### Frontend F5-S6 Recovery - DONE (commit 787e067, pushed; user screenshot reviewed)
- Replaced `/app/recovery/:id` with the alert-prefilled request: disruption/order/deadline, scenario-aware matching options, Ready / Approval Pending / Excluded / Other groups.
- Candidate cards show machine-checkable PASS/FAIL/UNKNOWN filters with basis/detail, unverified approval checks, capacity summaries, relationship status and ranking. Excluded or hard-filter-failing partners cannot be selected; selection goes through the approval disclaimer confirmation sheet.
- After selection, loads the consent-aware Jinja handover API and renders the Cream paper pack with authorised documents, job requirements, quantity/deadline, inspection checklist, required approvals, responsibilities, simulated milestones and explicit note that contacts aren’t in the API contract.
- Added M10 tracking rail with seven backend steps and one-step advance; every simulated value is labelled. Errors from selection/step advancement are surfaced.
- Browser smoke against live `rr_20261114173203_ord_102`: six candidates (Oragadam READY, Hosur APPROVAL_PENDING, Ambattur/Guindy excluded, Peenya STALE, Coimbatore potential); selected Oragadam, request ACTIVE, handover redacted and labelled, responsibilities/milestones visible, route card at REQUEST_SENT. No browser console errors.
- `npm test` 6/6; lint, palette lint, build pass. User-reviewed screenshot at 1366×768 shows request summary, Ready / Approval Pending / Excluded columns and unverified checks with no visual blocker. Screenshot attachment remains in chat; the browser tool could not copy it to `docs/screens/`.

### Frontend F5-S7 Partners & Readiness - DONE (commit a4cf09c, pushed; polish a7a14c4; user screenshot reviewed)
- Replaced the Partners placeholder with the relay circuit and partner drawer, 24/48/72 readiness ring/breakdown, stale/expiring preparedness review, score history chart, and next-best-action counterfactuals.
- Circuit uses live relationships and M6 exclusions/reasons, with solid/dashed/hatched paths. Drawer exposes all five checks, reconfirm, and guarded status changes; backend `409 details.missing_checks` is rendered as CANNOT SET READY.
- “Do it” confirms the counterfactual delta, then completes pending checks + READY or reconfirms. Verified with Hosur: 53.9 → 70.9 weighted (+17); score/history updated. Demo DB reset after smoke run.
- `npm test` 6/6; lint, palette lint, build pass. User screenshot at 1366×768 reviewed: relay circuit, readiness, review, action and history are legible. Moved the weighted score label below the ring to avoid overlapping the gauge. Screenshot attachment is in chat and could not be copied locally via browser tools.
- No Passports work has started; wait for confirmation before F6.

### Frontend F6-S4 Passports & RFQ - DONE (commit 76f3998, pushed; screenshot reviewed)
- Added the five-step Drawing → Review → Confirm → Redacted RFQ → Share flow. Sample tray has Pump shaft / Piston rod / Valve flange; sample PNGs + PDFs are served locally from `frontend/public/drawings/`. File picker and drop target accept PDF/PNG/JPG. No Gemini calls are needed for golden samples; repeated-provider 429s are not retried from the UI.
- Extraction pending state uses a scan line only while the request is actually in flight. Provider/latency/degraded metadata is displayed. Rules-only mode has the explicit fallback banner. Manual draft remains available.
- Passport editor shows confidence/source per field, low-confidence disagreements and candidate picking, editable dimensions, route/material fields, missing-confirm requirements, and planner-cycle-time caveat. Confirmation calls backend and links the created part; edit changes are saved as user-confirmed.
- Confirmed passports show owner original and API-redacted RFQ sheets, redaction report, opaque `rfq_ref`, and RFQ/FULL share controls. FULL requires the explicit customer-permission dialog.
- Browser smoke using the local golden Pump shaft PNG: extraction returned in 1 ms, confirm created a part, RFQ redaction hid customer/drawing/part identifiers, structured and printable RFQ refs now render consistently in the UI, share consent dialog is present. No live Gemini call was made.
- **Backend mismatch fixed in Phase 14:** the RFQ builder now supplies one opaque reference to both the JSON field and printable text; regression tests enforce equality.
- `npm test` 6/6; lint, palette lint, build pass. User-reviewed 1366×768 screenshot shows sample tray, drawing sheet, confidence/source fields, review state, and consent workflow; no visual blocker. Screenshot is available in chat, not in the repo's docs/screens folder.
- Passports & RFQ was the last functional screen before the user authorized F7 Stage Controls & Presenter. Proof & Method and System were subsequently authorized and reviewed.

### Frontend F7-S9 Stage Controls & Presenter - DONE (screenshots reviewed)
- Replaced the Stage placeholder with the weather mode selector, current weather source/degraded badge, confirmed demo reset, API/DB/weather/vision readout, presenter toggle, projector/reduced-motion controls, scene quality, backdrop/sound, and snapshot preference. UI preferences persist locally; Stage drawer content scrolls independently on shorter screens.
- Added the 8-step presenter script (Appendix D, steps 0–7), elapsed timer, click navigation, `←`/`→`, `H` hide/show, and `R` reset. Reset returns to Desk with the Desk step selected and clears session/recovery demo state.
- Presenter Recovery steps route to the Recovery entry and, when available, the latest request handover. Recovery creation records that request ID for the presenter flow.
- Browser smoke: weather replay/synthetic switching; reset confirmation cancel; `R` called `POST /demo/reset` (200) and returned to Desk/step 1; presenter advanced through What-if, Recovery and Partners; `H` hid/restored the strip; accessibility/scene toggles applied and were restored to defaults. Stage readouts were healthy, and the reloaded browser had no console errors.
- User-reviewed screenshots show the Stage drawer hierarchy/readouts and Presenter strip; the drawer’s bottom controls were made scrollable after review. A reset-state mismatch found in the strip screenshot was corrected.
- `npm test` 6/6; `npm run lint`, `npm run lint:palette`, and `npm run build` pass.
- F7 screen implementations S9, S8 and S10 are reviewed. Snapshot data/capture was subsequently completed in F11; see the snapshot safety-net log below. Phase 14 was completed and tagged.

### Frontend F7-S8 Proof & Method - DONE (screenshot reviewed)
- Replaced the `/app/proof` placeholder with the Michaung exposure back-test table and score bars, four deterministic method summaries (exposure, weak points, matching, readiness), drawing-AI boundary, limits and data sources, and the six brief glossary terms. The Exposure CTA opens the screen with the live trace.
- Copied the seven sites and +22-point separation from the existing `docs/BACKTEST_EXPOSURE.md` report into static `frontend/src/data/backtest.json`; added a data integrity test. The page labels this as the existing M4 back-test, not the deferred Phase 14 integration gate, and notes that it is a small curated comparison rather than blind validation.
- User-reviewed screenshot at 2000×1000 shows the result, ranking bars/table, caveat, and start of the method cards clearly; no visual blocker.
- `npm test` 7/7; `npm run lint`, `npm run lint:palette`, and `npm run build` pass. Browser route/link smoke passed with no console errors.
- System screens (S10) were unstarted at this point in the log; they were later implemented and user-confirmed. Phase 14 required test suites have passed.

### Frontend F7-S10 System screens - DONE (user confirmed)
- Replaced both nested and app-wide unknown-route placeholders with the “Line not found” relay-contact screen and Back to Desk action.
- Added an AppShell health-error boundary for the full-page “Can’t reach the server” state with Retry and an enabled “Open saved snapshot” action. Snapshot-mode wiring and pack capture are now complete; see the snapshot safety-net log.
- Offline map-tile badges and vector/site-marker fallbacks were already implemented in Desk and Exposure; they remain intact.
- Browser smoke: nested and global 404 routes render and Back to Desk works; an isolated dev server pointed at an unreachable API showed the backend-unavailable page and the unavailable-snapshot explanation. User confirmed the System screens work as expected.
- `npm test` 7/7; lint, palette lint and build pass. Phase 14 required test suites have passed.

### Frontend F8 Landing hero - VISUAL SCREEN DONE (screenshot reviewed)
- Replaced `/` with the F8 hero: transparent nav, layered “FIND WHERE YOU BREAK” typography, serif subline, skyline, gantry crane, factory-bay grid with one lit bay, rain, chapter rail and anchored callout cards.
- Hero metrics come from the live dashboard and its auto stress test. When those calls fail, `src/data/story.fallback.json` supplies the previously verified replay values and the UI labels them “SAVED REPLAY · NOT LIVE”; this is not the full read-only snapshot pack.
- CSS/SVG hero is the static fallback. The procedural R3F scene is a separate lazy chunk and is selected by scene preference, device size, reduced-motion and WebGL support. `?tier=static` renders without requesting the scene chunk; a forced full-tier browser smoke mounted the WebGL canvas without console errors.
- User screenshot review requested brighter background; increased yard/facade contrast, grid visibility and 3D fill light. The refreshed screenshot shows the yard and lit bay clearly. “Watch the story” explains that scroll chapters arrive in F9; F9 implementation began and is now held at the user’s request during Phase 14 closeout.
- `npm test` 10/10; lint, palette lint and build pass. Vite reports the lazy HeroScene chunk at about 244 KB gzip; retain for the F11 performance pass. The 50+ fps budget remains unmeasured.
- Static fallback is procedural CSS/SVG rather than a captured `poster-hero.webp`; no poster capture was claimed. Poster/performance polish remains in F11.

### Phase 12 - DONE (commit 0ef204b, pushed)
- `scripts/make_sample_drawings.py`: 3 vector PDFs WITH text layers + 200-DPI PNGs (longest side <= 2000 px) + one deliberately messy variant (rotated 90 deg, contrast 0.45); title blocks with fictional customers; `expected.json` ground truth per drawing. Synthetic only - free-tier provider inputs may be stored by the provider (R9).
- `core/passport_rules.py`: deterministic regex/catalogue extractor (title-block labels with original casing, material catalogue + aliases incl. BS 970, ISO 2768 standard, Ra, HRC/coating lines copied exactly, dimension bands with max-deviation semantics, keyword process hints with word boundaries - a diameter symbol alone never implies TURN); validators (tolerance >= 0.001 mm, material in catalogue, quantity positive int); `merge()` implements the section 7.6 confidence table exactly (HIGH on normalised agreement, MEDIUM single-valid-source, LOW + NEEDS_REVIEW on invalid or disagreement with candidates shown and the rules value as default, MISSING otherwise); canonical storage (alias EN-8 -> EN8); the model's self-reported confidence is never read.
- `adapters/vision/`: `base.py` protocol; `cache.py` golden-by-SHA-256 (reads committed dir, writes to `FCD_GOLDEN_WRITE_DIR` in tests so the committed cache can never be polluted); `gemini.py` plain REST per the Phase 0 verified shape, temperature 0, JSON mode, 30 s timeout, one retry on 5xx, NO retry on 429 + 10-minute quota cooldown (module state, resettable in tests); `ollama.py` honest stub (D3 - always unavailable). Chain order from `VISION_PROVIDER_CHAIN`.
- `prompts/passport_extract.md`: null-when-not-visible, never guess, copy text exactly, millimetres, strict JSON schema.
- `services/passport.py`: ingest (SHA-256) -> prepare (PyMuPDF text layer + 200-DPI render) -> golden cache -> rules -> vision -> merge -> DRAFT with `extraction_meta` (provider/source/latency/sha256/degraded/warnings); successful Gemini results saved as golden. PATCH makes edited fields CONFIRMED/user. Confirm guard (route >= 1 step, material.grade, quantity, numeric tolerance or general standard; an invalid 0.0 tolerance is NOT trusted for step tolerances) then creates/updates the Part + `part_steps` with processes.yaml default cycle times (editable), tightest tolerance on the last machining step, vendor-batch processes outsourced.
- `core/redaction.py` + `templates/rfq.md.j2`: allow-list keeps only technical fields; deadline becomes "days from now" (datetime or ISO string); customer/drawing/part identifiers scrubbed from free text by exact string + regex; `redaction_report` (removed/scrubbed/kept); `rfq_ref` is opaque random (never the passport id); RFQ rows are stable per passport.
- Routers: POST /passports/extract (multipart), POST /passports/manual, GET/PATCH /passports/{id}, POST /passports/{id}/confirm, GET /passports/{id}/rfq?partner_id=, POST /passports/{id}/share. Partner view gates: RFQ share -> RFQ only; FULL share -> passport; none -> 403 FORBIDDEN.
- Tests: 41 new (258 total): rules-only accuracy vs expected.json (>= 80% gate, all core fields hit), merge table cases incl. the real pump-shaft tolerance disagreement, validators, alias normalisation; redaction allow-list/scrub/opaque-ref/deadline-days; API: cache extraction measured < 3 s (16 ms), vision failure -> rules draft (respx), 5xx retried exactly once, 429 -> one call + cooldown holds, messy image -> honest empty draft, manual create, PATCH -> CONFIRMED, confirm guard 409 + part/steps creation with default cycle times, RFQ leak test across fixtures (drawing no / part name / customer never appear in JSON or text), consent gate 403 / RFQ / FULL, stable rfq_ref.
- Live accuracy (task 9, `-m live` opt-in, excluded by default via addopts `-m 'not live'`): **100% (18/18) title-block fields, 2.6-3.5 s per drawing** -> `docs/TEST_REPORT.md`.
- Done-when: golden cache pre-generated for all 3 sample drawings (committed), cached extraction 16 ms, rules-only >= 80%, RFQ leak test green, consent gate 403 - the demo never depends on the network for vision.

### Phase 13 - DONE (commit ca0a4cd, pushed; Phase 14 tests were deferred at the time)
- `services/dashboard.py` implements the section 8.1 auto-run contract in order: exposure for owner + vendors + partners (TTL-cached weather, snapshot written) -> if alert, run or reuse the AUTO stress test (idempotent on factory_id + forecast_hash) -> top 3 SPOFs -> readiness 24/48/72 with the headline at the default window -> stale-partner count. One payload: factory, data_label SIMULATED SAMPLE, weather (mode/source/degraded/attribution), readiness {headline, windows}, alert {active, headline, onset, stress_test_id, cta=START_RECOVERY}, spof_top, exposure_summary (owner risk, routes, per-site risks), stale_partners.
- `api/dashboard.py`: GET /dashboard/{id} (409 NOT_AN_OWNER for partners) and POST /demo/reset (calls `reset_demo()`, clears the weather TTL cache, returns DemoStateOut; POST /demo/mode and GET /demo/state already live in the exposure router from Phase 7).
- Verified live: dashboard fires the alert (SEVERE, onset 23 h, headline text) with the auto stress test attached (deterministic id `str_auto_ff38b47a8b5aba43_fac_owner`), readiness 50.0/53.9 with windows 0/53.9/53.9, SPOF top 3 = heat vendor / grinder / EN24 supplier, 1 stale partner; POST /demo/reset rebuilds and the dashboard reproduces identically (same auto-stress id), now asserted in Phase 14.
- One schema lesson fixed live: the strict DashboardOut rejected an extra replay_event key - keep the payload exactly per schema; demo state carries the event name.
- Backend is feature-complete through the section 8 contract: health, M1 CRUD + relationships, M3 SPOF, M4 exposure/map, M5 stress, M6 matching, M7/M9/M10 recovery + handover + stepper, M2 passports + RFQ + sharing, M8 readiness, dashboard and demo controls. The Phase 14 end-to-end gate has now been run; see the Phase 14 log and `docs/TEST_REPORT.md`.

### Phase 14 - DONE (commit 70bca53; tag `backend-v1` pushed)
- Full regression: `271 passed, 1 deselected`; ruff clean. Branch-aware coverage: `app/core` 94%, `app/services` 90%.
- Suite B OpenAPI path/response-schema checks pass against `docs/openapi.snapshot.json`; key request schemas include examples. `backend/README.md` documents run/reset/modes.
- Suite C runs the complete replay story with Gemini credentials cleared: dashboard/auto stress, SPOF, golden passport + RFQ, matching, recovery handover/stepper, and Hosur readiness uplift.
- Suites D–J and K pass: forecast 500/timeout and cache/replay fallbacks; deleted DB reset; malformed image 422; five identical reset/dashboard cycles; ten parallel dashboard requests with one auto stress row; RFQ/consent and secret-log checks; guarded transitions; +22 Michaung separation; zero-key story.
- Performance sample: dashboard cold/warm 0.083/0.011 s; manual stress 0.032 s; matching 0.007 s; cached passport 0.025 s.
- Suite L (live Open-Meteo/Gemini) intentionally not run; it is informational/optional and no provider calls were needed. Suite M E: audit passes; TEMP/TMP are stale in this long-lived process but persisted user paths are on E: and there are no C: cache leaks.
- `docs/TEST_REPORT.md` and `docs/openapi.snapshot.json` are committed. Optional live smoke L was not run; no Gemini/Open-Meteo calls were made.

### Frontend F9 — Landing scroll story - DONE (reviewed)
- Added a reversible five-chapter pinned story with GSAP ScrollTrigger + Lenis, a static/mobile fallback, story callouts, partner relay, readiness close, and post-story method/proof/limits/CTA sections.
- Smoothed wheel response and camera transitions after user review. Honest replay labels are retained; sample values are not represented as live.
- User approved the final visuals and scroll feel. `npm test` 11/11, lint, palette lint and production build pass. Desktop Lenis interaction was previously smoke-tested without console errors; the final smoothing was build/test verified.

### Snapshot safety net — DONE
- Added `frontend/src/data/snapshot.json`, a 20-endpoint, `SIMULATED SAMPLE` replay capture covering dashboard, SPOF, exposure/map, relationships, readiness, stress test, recovery request/tracking/handover, and confirmed passport/RFQ, plus supporting screen queries.
- Added `backend/scripts/capture_frontend_snapshot.py`. It builds/captures in a temporary isolated SQLite database, uses replay and the committed golden drawing cache, makes no live provider calls, and leaves the developer demo database untouched.
- “Open saved snapshot” now enters `/app` without health/API requests. The persistent ribbon says “SAVED SNAPSHOT · NOT LIVE”, shows capture time, and offers a return-to-live action. The client resolves captured GETs locally, permits only the read-only matching search POST, and rejects all writes; persistent write controls are disabled.
- Recovery and passport navigation open their captured records automatically in snapshot mode. Read-only data views for Desk, Weak Points, Exposure, What-if, Recovery, Partners, Passports and Proof were browser-smoke-tested; the outage action was tested with backend requests blocked in the browser. No browser console errors or backend requests occurred after entering snapshot mode.
- Frontend tests 15/15, lint, palette lint, production build, and Ruff on the capture script pass. The 50+ fps/accessibility/rehearsal parts of F11 remain pending.

### Phase 17 — Frontend/backend replay integration - DONE
- Live replay browser smoke: Health, demo state, dashboard, exposure map/site, readiness/actions, auto stress test, SPOF/orders, matching, passport, RFQ, recovery request/tracking/handover, and relationships/readiness screens connected to the running API; checked responses returned 200 (recovery create returned 201).
- Exercised a manual Flood test (result rendered with 4 at-risk orders), golden-cache Pump Shaft extraction → confirm → redacted RFQ, then order `ord_102` recovery → Ready Oragadam selection → handover → tracking advance. No browser console errors.
- Partners integration completed Hosur's remaining checks and READY transition; weighted readiness rose **53.9 → 70.9 (+17)** and the backend readback confirmed `READY`.
- Presenter navigation visited What-if, Weak Points, Passports, Recovery request/handover and Partners. This exposed that What-if-created requests were not saved for Presenter steps 5–6; now those steps retain and reuse the created recovery ID.
- Backend scenario test: `pytest tests/scenario/test_demo_story.py -q` passed. Failure-injection tests: `pytest tests/phase14/test_failure_injection.py -q` passed (3 tests). Frontend tests 15/15, lint and palette lint pass.
- Reset the demo from Stage Controls at the end; backend is back in replay baseline. Browser snapshot mode was also exercised with backend fetches blocked and made no backend requests; the backend process itself was not stopped.
- Lighthouse checks on Desk and Landing scored 100 for accessibility, best practices and SEO; fixed low-contrast Landing footer links and added `public/robots.txt`. The app-shell audit retains one zero-weight mobile-label diagnostic; its overall accessibility score is 100.
- External Open-Meteo live mode was not run. The default minified Vite build now passes with one Rayon thread and a 1 GB Node heap; Vite retains its existing large-chunk warning (main gzip 143 KB; lazy HeroScene gzip 245 KB).
- F11/Phase 18 are still open: full-tier 50+ fps measurement, final projector/desktop viewport checks, three timed rehearsals, and final screenshots/tagging have not been completed.

### F11 progress — accessibility, rehearsals, reset concurrency fix
- **Accessibility:** Lighthouse on Desk and Landing scored 100 (accessibility, best practices, SEO). Fixed low-contrast Landing footer links and gave the palette button a matching accessible name. The app-shell audit keeps one zero-weight mobile-label diagnostic; its overall accessibility score is 100.
- **Rehearsals:** ran three scripted runs of the 8 presenter steps in replay mode, resetting between. Run 1 and run 2 completed every step; run 2 also drove the closing moment (Hosur checks + READY → readiness **53.9 → 70.9**, action consumed). Run 3 completed every step but logged one transient exposure error, which led to the fix below. A final run after the fix completed all steps with **zero console errors**.
- **Reset concurrency fix (real defect):** `POST /demo/reset` racing a background refetch returned HTTP 500 (surfaced as a CORS error because the 500 leaves the app outside the CORS middleware). Root causes: `reset_demo()` dropped the schema (not atomic on pysqlite) and `compute_exposure()` wrote the deterministic snapshot row without serialization. Now the reset wipes rows atomically and a shared `DEMO_WRITE_LOCK` serializes reset + snapshot writes. Full `pytest` passes; probes of reset racing exposure returned 80/80 HTTP 200 and reset racing six read endpoints returned 140/140 HTTP 200.
- **Not measurable in this environment:** the in-app browser never fires animation frames (the desktop window is not compositing) and does not deliver keyboard events to the page, so the full-tier 50+ fps measurement, the keyboard-only pass, and the 1920×1080 / 1366×768 viewport checks still need the demo machine. Rehearsal timing was not human-paced (tool round-trips dominate), so the "under 4 minutes" target is unverified.
- **README:** replaced the Vite template `frontend/README.md` with run steps, scripts, keyboard shortcuts, scene tiers, snapshot mode and the data-file list. The `v1.0` tag is deliberately not created until the remaining checks pass.

### F11 — freeze checks passed on the demo machine (user-run) + readability/copy pass
- User ran the four machine-dependent checks: full-tier performance is smooth (50+ fps), the keyboard-only pass works, nothing clips at 1920×1080 or 1366×768, and presenter mode runs cleanly. Screenshots supplied from the presenter's machine (see `docs/screens/final/`).
- **Readability pass:** raised the smallest type tiers across the CSS (`8px→10px`, `9px→10px`, `10px→11px`) using a script that edits only the size token inside `font:`/`font-size:` declarations, so no widths, gaps or paddings moved.
- **Copy pass:** API codes no longer reach the screen as raw snake_case. Added plain-language labels for exclusion reasons, readiness reasons, backup/order statuses, recovery status, hazard names, route steps and process codes (`lib/status.js`), and applied them on Desk, Partners, Recovery, Weak Points and the landing relay panel. Order ids now read "Order 104" instead of `ord_104` (the raw id is kept internally so broken-order highlighting still matches). Cryptic section kickers were rewritten ("RELAY CIRCUIT" → "BACKUP NETWORK · Who can cover your work", "COUNTERFACTUAL ACTIONS" → "WHAT WOULD RAISE YOUR SCORE", "SCORE HISTORY" → "How your readiness changed", "OPEN PART BREAKDOWN" → "OPEN PART-BY-PART BREAKDOWN"). The history chart now labels points with real timestamps instead of `72 h · 3`.
- Frontend tests 16/16 (added a test that reason codes are explained in plain language), lint, palette lint and the production build pass. Lighthouse: Landing and Desk both 100 (accessibility, best practices, SEO). All eight screens browser-checked with zero console errors.
- **Note:** the dev server had to be restarted once — it was serving a stale `Landing.jsx` transform, which briefly showed an "Unexpected Application Error" and a false Lighthouse `landmark-one-main` failure. The source was valid; a clean rebuild and fresh dev server cleared it. Verified against the production build.
- **Still not renamed:** seeded demo entity names still read "Sample …" (e.g. "Sample Engineering (Hosur)"), and internal ids such as `fac_owner` / `ven_heat` still appear on engineering nameplates. Renaming those touches the backend seed, the snapshot pack and the data tests, so it is held for an explicit decision.

### Phase 18 — Freeze and submission - DONE (`v1.0` tagged)
- All F11 checks are complete. The four machine-dependent checks were run by the user on the demo machine: full-tier performance is smooth (50+ fps), the keyboard-only pass works, nothing clips at 1920×1080 or 1366×768, and presenter mode runs cleanly. The human-paced rehearsal is under the 4-minute budget.
- Freeze screenshots are committed to `docs/screens/final/` (Desk, What-if, Weak Points) and document the readability/copy pass. The remaining screens were not captured because automated screenshots are unavailable in this environment.
- Final state: frontend tests 16/16, lint, palette lint and the production build pass; backend `pytest` and `ruff` pass; Lighthouse 100 (accessibility, best practices, SEO) on Landing and Desk; no console errors across the eight screens.
- Optional work deliberately not done: F10 persistent world backdrop (cut as a stretch) and the external live-provider smoke (suite L). Neither is required by the brief; the demo runs fully offline on replay.

### Post-freeze — deployment prep (additive; `v1.0` unchanged)
- Added `docs/DEPLOY.md` plus host configs: `render.yaml` (Render blueprint, at the repository root — Render only discovers it there — with `rootDir: backend`), `backend/railway.json`, and `frontend/vercel.json` (Vite build + SPA rewrites so `/app/...` deep links work).
- Added `backend/scripts/ensure_demo_world.py`: seeds the sample world only when the database is empty, so a fresh host comes up in the replay baseline and an existing database is left alone. Verified both paths locally against an isolated SQLite file (fresh run seeded 7 factories / 33 machines / 8 orders; second run skipped; the dashboard then read back weighted 53.9 with 3 weak points).
- Chosen shape: frontend on Vercel, backend on Render or Railway with a writable disk. Vercel-only was rejected because its filesystem is read-only except `/tmp` (SQLite would reset on cold start) and the Python bundle (PyMuPDF + numpy + shapely) sits near Vercel's ~250 MB function limit.
- Recorded the free-tier caveats honestly in `docs/DEPLOY.md`: SQLite resets without a disk, cold starts can exceed the 8 s client timeout, process-local write locks mean one instance only, and there is no auth. Deployment was **not** required by the submission checklist (repo link, README, demo video, labelled sample data, attributions).
- No application behaviour changed. Backend `pytest` + `ruff` and the frontend production build still pass.
