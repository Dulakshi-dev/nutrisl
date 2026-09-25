# Deploying NutriSL to Vercel

This project deploys as **two separate Vercel projects** from the same repo: one for
`backend` (FastAPI) and one for `frontend` (Vite/React). This is the standard pattern
for a split frontend/backend app — Vercel doesn't run one service that's both.

The backend's SQLite database (`backend/data/nutrisl.db`) is read-only at runtime
(the app only queries it, never writes to it), so it's safe to ship as a bundled
file inside the serverless function. `backend/vercel.json` and `backend/api/index.py`
are already set up for this.

## 1. Push this folder to GitHub
Create a new repo (e.g. `nutrisl`) and push this whole folder (backend + frontend)
to it. Vercel deploys straight from a GitHub repo.

## 2. Deploy the backend
1. In Vercel: **Add New → Project → Import** your repo.
2. Set **Root Directory** to `backend`.
3. Framework preset: **Other** (Vercel will detect the Python function automatically
   from `api/index.py` + `requirements.txt`).
4. Deploy. Note the resulting URL, e.g. `https://nutrisl-backend.vercel.app`.
5. Test it: visit `https://nutrisl-backend.vercel.app/health` — should return `{"status":"ok"}`.

## 3. Deploy the frontend
1. **Add New → Project → Import** the same repo again, as a second project.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Vite** (auto-detected).
4. Add an environment variable: `VITE_API_URL` = your backend URL from step 2
   (no trailing slash), e.g. `https://nutrisl-backend.vercel.app`.
5. Deploy.

## 4. Sanity check
Open the frontend URL, fill in a profile + a food diary entry, and run an analysis.
If it fails, check the browser console for the exact API URL it's calling — it should
match your backend deployment.

## Notes / things to tighten before this goes further than a review demo
- `backend/app/main.py` has CORS wide open (`allow_origins=["*"]`) — fine for now,
  restrict to your frontend's domain before any real users touch it.
- The SQLite file is bundled read-only into the function. If you ever need to write
  to it (e.g. saving user accounts/history), you'll need a real hosted database
  instead (Vercel Postgres, Supabase, etc.) — serverless functions don't persist
  local file writes between requests.
