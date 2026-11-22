# Deploying RELAY

Two hosts, one link for the reader:

| Part | Host | Why |
|---|---|---|
| `frontend/` | Vercel | Static Vite build, free, instant |
| `backend/` | Render or Railway | FastAPI + SQLite needs a real writable disk |

Vercel alone is possible but a poor fit: its filesystem is read-only except
`/tmp`, so SQLite would reset on every cold start, and the Python function
bundle (PyMuPDF + numpy + shapely) sits close to Vercel's ~250 MB limit.

Everything below is free-tier friendly. Nothing here changes the demo behaviour
or the `v1.0` tag.

---

## 1. Backend on Render

1. Render dashboard → **New → Blueprint** → pick this repository.
2. Render reads `render.yaml` **at the repository root** and creates the
   `relay-api` service. The service itself is scoped to `backend/` through
   `rootDir`, so Render only sees the backend.
3. Set the one unset variable when prompted:
   - `CORS_ORIGINS` = `https://<your-frontend-domain>` (comma-separate extra
     origins, e.g. Vercel preview URLs).
4. Deploy. The start command is:

   ```
   python scripts/ensure_demo_world.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

   `ensure_demo_world.py` seeds the sample world on a fresh instance and leaves
   an existing database untouched.
5. Check `https://<service>.onrender.com/api/v1/health` returns
   `{"status":"ok", ...}`.

**Railway instead:** New Project → Deploy from GitHub → set the service **root
directory** to `backend`, then add the same variables. `backend/railway.json`
already carries the start command and health check. (Railway, unlike Render,
does read its config from the service directory.)

### Backend variables

| Key | Value | Notes |
|---|---|---|
| `PYTHON_VERSION` | `3.12.10` | matches local |
| `APP_ENV` | `production` | |
| `WEATHER_MODE` | `replay` | keeps the demo off the live forecast |
| `CORS_ORIGINS` | `https://<frontend-domain>` | must match exactly, scheme included |
| `DATABASE_URL` | unset | defaults to `backend/data/fcd.sqlite`; on a host with a disk, point it at the mount (e.g. `sqlite:////var/data/fcd.sqlite`) |
| `GEMINI_API_KEY` | unset | optional. Without it, drawings come from the committed golden cache — the demo path |

Never commit `.env`; it is already git-ignored.

---

## 2. Frontend on Vercel

Import the repository at its **root** — do not change the Root Directory.
Vercel reads the root `vercel.json`, which installs and builds `frontend/` and
publishes `frontend/dist`, plus the SPA rewrites that keep `/app/...` deep links
working.

1. Vercel → **Add New → Project** → import this repository (root directory left
   as the default `./`).
2. If Vercel offers a framework preset, leave it as **Other**; the root
   `vercel.json` already carries the install, build and output settings.
   (`frontend/vercel.json` is kept for the alternative where you set Root
   Directory to `frontend`; use one approach or the other, not both.)
3. **The API URL is committed** in `frontend/.env.production`, which Vite loads
   for production builds only. Nothing has to be configured in the dashboard,
   and `npm run dev` still points at `localhost:8000`.

   The optional dashboard variable below **overrides** that file if you ever
   need a different backend. Note that a host environment variable set to an
   empty string also overrides it — if the deployed site calls `localhost`, check
   for a blank `VITE_API_URL` and delete it.

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://<your-backend-domain>/api/v1` |

   It is read at build time, so redeploy after changing it.
4. Deploy, then go back to the backend and make sure `CORS_ORIGINS` is exactly
   the domain Vercel gave you.

---

## 3. Verify

1. Open the frontend URL. The status strip should read `API` (not `OFFLINE`)
   and `Replay`.
2. Desk shows the alert banner, readiness ring and top-3 weak points.
3. Run one write to prove the disk is writable: **Desk → Start recovery
   request**, or **Partners → Do it** on the next best action.
4. If the backend is asleep, the first load may take ~30 s on a free tier. The
   client times out at 8 s and shows "Can't reach the server" — press **Retry**,
   or use **Open saved snapshot** for the read-only demo.
5. Open the browser console once and confirm no CORS errors. A CORS error almost
   always means `CORS_ORIGINS` does not match the frontend origin exactly.

---

## 4. Free-tier caveats (state them honestly)

- **SQLite resets.** Render's free plan has no persistent disk and spins down
  after inactivity; the container filesystem is lost on redeploy or restart.
  The world always comes back to the same seeded replay baseline, but recovery
  requests and readiness changes you made are gone. Add a disk (paid) or set
  `DATABASE_URL` to the mount path if you need persistence.
- **Cold starts.** The first request after a spin-down can exceed the client's
  8 s timeout. Press Retry.
- **Single instance.** The write locks are process-local, so do not scale the
  service to multiple instances against one SQLite file.
- **No auth.** Every endpoint is open by design; this is a demo, not a product.
- **Live weather and live vision are not enabled.** `WEATHER_MODE=replay` plus
  no `GEMINI_API_KEY` keeps the demo deterministic and key-free.
