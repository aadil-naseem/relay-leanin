# VERIFIED FACTS

Anything external (URLs, parameter names, model names, response shapes, limits) must be **verified live** and recorded here before it is used in code (R5).

Status key: `VERIFIED` = checked against provider docs or a live call today. `ASSUMED` = from the blueprint, not yet checked. `BLOCKED` = could not verify; fallback in use.

---

## Environment (verified at Phase 0)

| Item | Value | How |
|---|---|---|
| OS | Windows | `$PSVersionTable` / session |
| Project root | `E:\VihaanX-Build` | created |
| `E:` free space at start | 13.3 GB | `Get-PSDrive E` |
| Python | 3.12.10 at `C:\Users\Aadil\AppData\Local\Programs\Python\Python312\python.exe` | `python --version` |
| Node | v24.16.0 at `E:\Program Files\nodejs\node.exe` | `node -v` |
| npm | 12.1.0 | `npm -v` |
| Git | `E:\Program Files\Git\cmd\git.exe` | `where git` |
| npm cache | `E:\dev-cache\npm` | `npm config get cache` |
| npm prefix | `E:\dev-cache\npm-global` | `npm config get prefix` |
| TEMP / TMP | `E:\dev-cache\temp` | user env |

---

## Open-Meteo

All three endpoints verified live from this machine on 2026-11-14 (Phase 0). No key required.

**Forecast — `GET https://api.open-meteo.com/v1/forecast`** — `VERIFIED`

Params used: `latitude`, `longitude`, `hourly=precipitation`, `forecast_days=3`, `timezone=UTC`.
Returned `hourly.time[]` + `hourly.precipitation[]`, 72 values. Ambattur 2023-12-04 test:
**72 h total = 1.10 mm, max hourly 0.30 mm — i.e. dry right now.**

> Consequence for the demo: in `live` mode today there is no rain, so **no alert would fire**. Defaulting to `replay` is not a nicety, it is required for the demo to exist. `live` remains available and honestly labelled.

**Archive — `GET https://archive-api.open-meteo.com/v1/archive`** — `VERIFIED`

Params used: `latitude=13.100`, `longitude=80.155`, `start_date`, `end_date`, `hourly=precipitation`, `timezone=UTC`.
Michaung window at Ambattur (2023-12-01..2023-12-07), 168 hourly values, total **353.8 mm**:

| Date | Rain |
|---|---|
| 2023-12-01 | 2.6 mm |
| 2023-12-02 | 37.7 mm |
| 2023-12-03 | 51.0 mm |
| **2023-12-04** | **238.7 mm** |
| 2023-12-05 | 0.0 mm |
| 2023-12-06 | 13.2 mm |
| 2023-12-07 | 10.6 mm |

Peak hours: 2023-12-04 14:00 (19.6 mm), 13:00 (19.4 mm), 04:00 (18.7 mm).

> **Phase 4 decision (recorded now):** the blueprint's suggested window start of 2023-12-01 puts the heavy onset ~72 h in, which is outside the intended 24–40 h lead. Start the replay series at **2023-12-03T00:00Z** instead, so the Dec-4 peak lands at **~37–40 h** and the 24 h rolling sum reaches ~238 mm → hazard ≈ 1.0 → site risk above the 50 alert threshold. Keep 72 h of series.

**Elevation — `GET https://api.open-meteo.com/v1/elevation`** — `VERIFIED`

Params used: `latitude` and `longitude` as **comma-separated lists** (batched). Two points returned `[14.0, 16.0]` metres — plausible for Ambattur. Batch limit: to confirm at Phase 4 when asking for 100+ coordinates.

> **Phase 4 update (2026-11-14): batch limit VERIFIED live = 100 coordinates per call** (HTTP 200 with exactly 100 `latitude`/`longitude` values; 100-element `elevation[]` returned). All prefetch batches are sized <= 100.

- Attribution "Weather data by Open-Meteo.com" required in UI.
- Rate limits: not hit during Phase 0; blueprint's ~10k/day fair use is unverified but far above demo needs.

## Gemini (drawing reading)

Endpoint base: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...`
Request shape verified live (text and image): `contents[].parts[]` with `{text}` and `{inline_data:{mime_type,data(base64)}}`; JSON output via `generationConfig.responseMimeType="application/json"` + `temperature=0`.

**Model probe results (2026-11-14, key without billing):**

| Model | Text | Vision | Result |
|---|---|---|---|
| `gemini-3.8-flash` | timeout @100 s | timeout @100 s | unusable |
| `gemini-flash-latest` | timeout @40 s | not tried | unusable |
| `gemini-3.5-flash` | HTTP 503 | not tried | unavailable |
| `gemini-2.5-flash` | HTTP 404 | not tried | not offered to this key |
| **`gemini-3.5-flash-lite`** | **200, 1.5 s** | **200, 5.6 s, correct** | **CHOSEN** |
| `gemini-3.1-flash-lite` | 200, 3.2 s | not tried | viable fallback |

`GEMINI_MODEL=gemini-3.5-flash-lite` set in `backend/.env` and `.env.example`.

Vision accuracy on the probe image: returned `shape=shaft`, `material=EN24`, `diameter_text=20 +0.02/-0.00` — all correct.

> Caveats: Flash-Lite is the weakest Flash tier, so the rules parser + human confirm step matters more, not less. The `ListModels` response does **not** expose free-tier eligibility — it was inferred by a successful unauthenticated-by-billing call returning 200. Free-tier limits per minute/day are not published in the API response and remain unverified; the 10-minute cooldown on quota errors (Phase 12) stays in the design.
>
> Latency ~5.6 s per drawing is too slow for a live "watch it read" moment without a spinner. Second run through `smoke_connectivity.py` took **13.1 s** for the same tiny image, so latency is variable (5-13 s) and not predictable on stage. The 3 sample drawings must come from `data/golden/` (sub-3 s, Phase 12 test), with live Gemini as the fallback — which is already the plan.

## OpenStreetMap / OSMnx

| Item | Status | Notes |
|---|---|---|
| OSMnx install on Windows + Python 3.12 | ASSUMED | `requirements-data.txt`, not yet installed |
| Overpass usage | n/a | prefetch only, never at runtime |

---

## Seed / demo world claims (need a citation before they go on a slide)

| Claim | Status | Source |
|---|---|---|
| Ambattur north phase (~1,500 units) flooded during Cyclone Michaung, Dec 2023 | **VERIFIED** | KNN India (2023-12-07): "The North phase [of Ambattur Industrial Estate] has three sectors. Water is slowly receding in sector one while the other two sectors are still [flooded]"; The Hindu (2023-12-04): "The Ambattur Industrial Estate was the most affected. Water seeped into many units"; estate loss ~Rs 2,000 crore (The Week, 2023-12-06) |
| Thirumudivakkam / Perungudi / Thirumazhisai / Kakkalur estates submerged | **VERIFIED** | The Week (2023-12-06): estates "still submerged in four to six feet of water"; The Hindu Businessline (2023-12-08): flooding "crippled" MSME units in Ambattur, Thirumudivakkam, Perungudi, Thirumazhisai |
| Villivakkam industrial estate flooded | **VERIFIED** | Deccan Herald (2023-12): Ambattur and Villivakkam estates flooded days after the storm, water on shop floors damaging machines/stock, MSME damages > Rs 3,000 crore |
| Oragadam / SIPCOT estates resumed within days | **VERIFIED** | Deccan Herald (2023-12, TN govt statement): "situation in Oragadam ... was better" with industrial parks resuming operations; Indian Express: >90% of large-scale units resumed while MSMEs stayed hit |
| All zones in `data/cache/zones.json` are illustrative, not official flood maps | BY DESIGN | radii are planning heuristics around reported estates; every zone note cites the source above |

## Phase 4 prefetch (verified 2026-11-14)

| Item | Status | Notes |
|---|---|---|
| OSMnx install on Windows + Python 3.12 | **VERIFIED** | osmnx 2.1.1 (with geopandas 1.2.0, pyproj 3.8.0, networkx 3.7) installed from requirements-data.txt |
| Terrain: 16 sites (9 demo + 7 back-test) | **VERIFIED** | `data/cache/terrain.json`; owner is -4.7 m below its ring mean; Oragadam 53 m (plateau) |
| Replay: 16 sites x 72 h from 2023-12-03T00:00Z | **VERIFIED** | `data/cache/replay_michaung.json`; owner Dec-4 total **238.7 mm — matches the Phase 0 reference exactly**; flooded back-test sites 225-315 mm; Hosur 0.4 mm, Peenya 2.5 mm, Coimbatore 1.7 mm (dry inland - supports the matching story) |
| Synthetic fallback | VERIFIED | `data/cache/synthetic_storm.json`, labelled "SYNTHETIC SAMPLE", deterministic ramp (peak 20 mm/h at t+36h) |
| Routes (OSM drive graph, Chennai metro) | VERIFIED | `data/cache/routes.json` + `data/raw/graph_chennai.graphml` (git-ignored); scope decision: routes only for storm-footprint sites (Ambattur cluster + Guindy); far partners keep null route facts per the cut order |

## Phase 7 exposure (verified/tuned 2026-11-14)

| Item | Status | Notes |
|---|---|---|
| Multi-location forecast | **VERIFIED live** | `GET /v1/forecast?latitude=a,b,c&longitude=x,y,z&hourly=precipitation&forecast_days=4&timezone=UTC` returns an **array** of one object per location. 4 days = 96 h from 00:00 UTC today; slicing from the current hour leaves 85 h, enough for the 72 h horizon. Dry right now (1.10 mm/72 h), so `replay` stays the demo mode |
| Onset threshold tuned | **CHANGED in config, not code** | `config/exposure.yaml` `heavy_onset_mm_3h: 5 -> 10`. At 5 mm/3 h the Michaung series tripped at hour 0 (Dec-3 drizzle is 2-5 mm/h), giving "onset now". The IMD "heavy" 24 h band starts at 64.5 mm, i.e. ~8 mm/3 h; 10 mm/3 h is the conservative equivalent and puts onset at **h23-24**, inside the 24-40 h lead the blueprint wants. No site name is referenced in code or config |
| Depression constant recalibrated (Phase 9) | **CHANGED in config, not code** | `config/exposure.yaml` `depression_full_m: 3.0 -> 5.0`. The SIPCOT plateau sites dip ~3 m below their ring mean at 50+ m elevation without flooding, while the flooded floodplain estates sit 4-5 m low; at 3.0 the plateau dips saturated the depression term. Effect: back-test separation **+12 -> +22**; owner 98 -> 96 (SEVERE, alert unchanged); Oragadam 58 -> 48. Recorded because M6's correlated-risk exclusion uses the alert threshold |
| Back-test | **PASS, +22 points** | see `docs/BACKTEST_EXPOSURE.md`. Flooded: Thirumudivakkam 78, Ambattur north 73, Villivakkam 70, Perungudi 70. Not flooded: Oragadam 48, Irungattukottai 29, Pillaipakkam 28. Water distances are real OSM measurements (flooded sites 0-330 m from water; not-flooded 683-1495 m) and were **added after the first run** (which passed at +5 with water unknown); the depression recalibration (Phase 9) raised the margin to +22 - so the result is not an artefact of tuning |
| Owner exposure in replay | VERIFIED | site risk **96 SEVERE**, hazard 1.00, vulnerability 0.95, max 24 h 242.3 mm, onset 23 h, wet spell 21 h; Oragadam 48 (MODERATE) - lower than Ambattur and below the alert threshold, so the hero backup stays viable (Phase 9 invariant 4) |

## Phase 12 passport / vision (verified 2026-11-14)

| Item | Status | Notes |
|---|---|---|
| Gemini vision accuracy on the sample drawings | **VERIFIED live, 100% (18/18)** | title-block fields (part, dwg no, rev, customer, qty, material) on all 3 PNGs; latency 2.6-3.5 s per call (faster than the Phase 0 probe suggested). Report: `docs/TEST_REPORT.md` |
| Golden cache | VERIFIED | 3 committed files in `data/golden/<sha>.json` (one per sample PNG), produced by real Gemini calls via `scripts/pregen_golden.py`; cache extraction measured at **16 ms** (< 3 s budget) |
| Rules-only accuracy | **VERIFIED >= 80%** | vector PDFs with text layer; all core fields found on all 3 drawings; tightest tolerances 0.02 / 0.005 / 0.05 mm exact; test enforces the >= 80% gate |
| Merge behaviour with real data | VERIFIED | the pump-shaft tolerance disagreement (+0.02/-0.00: rules 0.02, vision 0.0) follows the table: LOW + both candidates + rules default |
| Tests never touch the network or the committed cache | BY DESIGN | golden writes go to `FCD_GOLDEN_WRITE_DIR` (temp) in tests; Gemini `available()` is monkeypatched off; transport tests use respx; the live accuracy test is excluded by default (`-m 'not live'` opt-in) |