import type { NextConfig } from "next";

/** Base URL for FastAPI (phase6): /ui-api/*, /health/detailed. No trailing slash. Not a Streamlit URL. */
function backendOrigin(): string {
  const raw = process.env.BACKEND_URL || "http://127.0.0.1:8010";
  return raw.replace(/\/+$/, "");
}

function backendLooksLikeStreamlit(): boolean {
  const raw = process.env.BACKEND_URL || "";
  return /streamlit\.app/i.test(raw);
}

function effectiveBackendMode(): "streamlit" | "fastapi" {
  const explicit = process.env.NEXT_PUBLIC_BACKEND_MODE;
  if (explicit === "streamlit") return "streamlit";
  if (explicit === "fastapi") return "fastapi";
  // Safety net: if BACKEND_URL is actually a Streamlit URL, avoid FastAPI proxy mode.
  return backendLooksLikeStreamlit() ? "streamlit" : "fastapi";
}

const mode = effectiveBackendMode();
const inferredStreamlitUrl = backendLooksLikeStreamlit() ? backendOrigin() : "";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_BACKEND_MODE: process.env.NEXT_PUBLIC_BACKEND_MODE || mode,
    NEXT_PUBLIC_STREAMLIT_APP_URL: process.env.NEXT_PUBLIC_STREAMLIT_APP_URL || inferredStreamlitUrl,
  },
  async rewrites() {
    if (mode === "streamlit") {
      // Streamlit-connected deploy does not use FastAPI proxy routes.
      return [];
    }
    const backend = backendOrigin();
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
