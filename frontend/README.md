# RELAY frontend

React + Vite client for the Factory Continuity Desk demo. It renders the landing
story and the eight app screens against the FastAPI backend, and it can run the
whole demo read-only from a saved replay snapshot when the backend is down.

## Run locally

Start the backend first (see `backend/README.md`), then:

```powershell
npm install
npm run dev
```

- App: `http://localhost:5173/`
- Desk and screens: `http://localhost:5173/app`
- Landing static fallback: `http://localhost:5173/?tier=static`

The API base URL defaults to `http://localhost:8000/api/v1`. Override it with
`VITE_API_URL` when the backend runs elsewhere.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build |
| `npm test` | Node test runner (`tests/`) |
| `npm run lint` | Oxlint |
| `npm run lint:palette` | Enforce the 12-colour palette |

On a memory-constrained host the build may need one Rayon thread and a smaller
Node heap: `RAYON_NUM_THREADS=1 NODE_OPTIONS=--max-old-space-size=1024 npm run build`.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `1`–`8` | Jump to a screen |
| `` ` `` | Toggle Stage Controls |
| `/` or `Ctrl/Cmd+K` | Command palette |
| `Esc` | Close palette or drawer |
| `→` / `←` | Next/previous presenter step (presenter mode) |
| `R` | Reset demo (presenter mode) |
| `H` | Hide/show the presenter strip |

## Scene tiers and failure modes

- `useSceneTier` picks `full`, `lite` or `static` from the scene preference,
  device size, reduced-motion and WebGL support. Force one with `?tier=static`
  (or `full`/`lite`). The 3D hero is a lazy chunk and is not requested in
  `static`.
- If the backend is unreachable, the app shows "Can't reach the server" with
  Retry and **Open saved snapshot**.
- Snapshot mode serves `src/data/snapshot.json` locally, blocks every write, and
  shows the "SAVED SNAPSHOT · NOT LIVE" ribbon. Regenerate the pack with
  `backend/scripts/capture_frontend_snapshot.py`.

## Data files

| File | Source |
|---|---|
| `src/data/backtest.json` | Michaung back-test from the Phase 14 report |
| `src/data/story.fallback.json` | Verified replay values for the landing |
| `src/data/snapshot.json` | Read-only offline pack (isolated replay capture) |
| `src/data/exposureGeometry.json`, `scenarioScopes.json` | Map zones and scenario scopes |

All demo factories, orders and people are fictional samples. Weather, terrain and
road data are real; risk is an indicator, not a flood model.
