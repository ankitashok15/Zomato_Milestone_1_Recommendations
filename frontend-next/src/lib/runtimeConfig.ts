/**
 * Build-time public config (set in Vercel / .env.local).
 * Streamlit hosts the Python recommender UI; FastAPI exposes /ui-api JSON for this Next app.
 */

export const STREAMLIT_APP_URL = (process.env.NEXT_PUBLIC_STREAMLIT_APP_URL || "").replace(/\/+$/, "");

/** `streamlit` = recommender runs on Streamlit Cloud (no FastAPI proxy). Default `fastapi`. */
export const BACKEND_MODE = process.env.NEXT_PUBLIC_BACKEND_MODE === "streamlit" ? "streamlit" : "fastapi";

export function isStreamlitBackendMode(): boolean {
  return BACKEND_MODE === "streamlit" && Boolean(STREAMLIT_APP_URL);
}
