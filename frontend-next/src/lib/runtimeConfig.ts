/**
 * Build-time public config (set in Vercel / .env.local).
 * Streamlit hosts the Python recommender UI; FastAPI exposes /ui-api JSON for this Next app.
 */

/** Default Streamlit deploy when `NEXT_PUBLIC_BACKEND_MODE=streamlit` and no custom URL is set. */
export const DEFAULT_STREAMLIT_APP_ORIGIN = "https://zomatorecommendations.streamlit.app";

const trimmedEnv = (process.env.NEXT_PUBLIC_STREAMLIT_APP_URL || "").replace(/\/+$/, "");
const explicitMode = process.env.NEXT_PUBLIC_BACKEND_MODE;

/** `streamlit` = recommender runs on Streamlit Cloud (no FastAPI proxy). Default `fastapi`. */
export const BACKEND_MODE =
  explicitMode === "streamlit"
    ? "streamlit"
    : explicitMode === "fastapi"
      ? "fastapi"
      : trimmedEnv
        ? "streamlit"
        : "fastapi";

export const STREAMLIT_APP_URL =
  trimmedEnv || (BACKEND_MODE === "streamlit" ? DEFAULT_STREAMLIT_APP_ORIGIN.replace(/\/+$/, "") : "");

export function isStreamlitBackendMode(): boolean {
  return BACKEND_MODE === "streamlit" && Boolean(STREAMLIT_APP_URL);
}
