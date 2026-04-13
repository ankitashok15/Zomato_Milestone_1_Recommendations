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
- **Next.js (Vercel):** set project **Root Directory** to `frontend-next`. Set **`BACKEND_URL`** to your **FastAPI HTTPS origin** (not the Streamlit URL). Optional **`NEXT_PUBLIC_STREAMLIT_APP_URL`** for the header link to Streamlit.

Raw Hugging Face snapshots are gitignored; run `python phase2/src/ingest_zomato.py` to refresh `phase2/data/processed/`.
