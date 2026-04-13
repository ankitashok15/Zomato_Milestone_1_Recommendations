# Zomato AI restaurant recommender

Phase-based pipeline (ingestion → preferences → retrieval → LLM → API) with **FastAPI**, **Streamlit**, and **Next.js** UIs. See `phase_wise_architecture.md` for design detail.

## Quick start (local)

1. **Environment:** copy `.env.example` → `.env` and set `RECOMMENDATION_API_KEY`, `GROQ_API_KEY`.
2. **Python API:** from repo root, `python -m pip install -r phase6/requirements.txt` then  
   `python -m uvicorn phase6.src.recommendation_api:app --reload --host 127.0.0.1 --port 8010`
3. **Next.js:** `cd frontend-next` → `npm install` → create `.env.local` from `.env.local.example` (`BACKEND_URL=http://127.0.0.1:8010`) → `npm run dev` → [http://localhost:3000](http://localhost:3000)
4. **Streamlit:** `pip install -r requirements.txt` → `streamlit run streamlit_app.py` (needs `phase2/data/processed/` CSVs).

## Deployed apps

- **Streamlit:** configure secrets (`GROQ_API_KEY`, etc.) on [Streamlit Community Cloud](https://streamlit.io/cloud); main file `streamlit_app.py`, packages `requirements.txt`.

### Vercel (Next.js) — root directory must be `frontend-next`

The Next.js app lives only under **`frontend-next/`**. Vercel must use that folder as the **Root Directory**, or the build will look at the repo root and fail (no `package.json` there).

#### Option A — Dashboard (first deploy)

1. Open [vercel.com](https://vercel.com) → **Add New…** → **Project**.
2. **Import** your Git repo (`Zomato_Milestone_1_Recommendations`).
3. **Before** clicking **Deploy**, open **Build and Output Settings** (or **Configure Project**).
4. Find **Root Directory** → **Edit** → set exactly:

   `frontend-next`

5. Framework should auto-detect **Next.js**. If not, choose **Next.js** manually.
6. Add **Environment Variables** (Production — and Preview if you use it).

   **Connect Vercel to Streamlit only** (no FastAPI):

   | Name | Value |
   |------|--------|
   | `NEXT_PUBLIC_BACKEND_MODE` | `streamlit` |
   | `NEXT_PUBLIC_STREAMLIT_APP_URL` | `https://zomatorecommendations.streamlit.app` (no trailing `/`) |

   **Use the Next.js form + metrics** (requires a real API):

   | Name | Value |
   |------|--------|
   | `BACKEND_URL` | `https://your-fastapi-host` (HTTPS, **no** trailing `/`) |
   | `NEXT_PUBLIC_BACKEND_MODE` | `fastapi` or leave unset |

   Optional in either setup: `NEXT_PUBLIC_STREAMLIT_APP_URL` for an extra **Streamlit app** link in the header.

7. **Deploy**. If you change `BACKEND_URL` or any `NEXT_PUBLIC_*` variable, trigger a **Redeploy** (rewrites and public env are baked in at build time).

#### Option B — Dashboard (project already exists, build failed)

1. Open the project on Vercel → **Settings** → **General**.
2. **Root Directory** → **Edit** → enter `frontend-next` → **Save**.
3. **Deployments** → open the latest → **⋯** → **Redeploy**.

#### Option C — CLI (no Root Directory field needed)

From your machine, with the repo cloned:

```bash
cd frontend-next
npx vercel login
npx vercel link    # create or link a project
npx vercel --prod
```

Vercel uses the current directory (`frontend-next`) as the app root.

---

Raw Hugging Face snapshots are gitignored; run `python phase2/src/ingest_zomato.py` to refresh `phase2/data/processed/`.
