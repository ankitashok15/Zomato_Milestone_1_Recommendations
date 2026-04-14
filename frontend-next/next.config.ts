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

function backendLooksPrivateOrLocal(): boolean {
  const raw = (process.env.BACKEND_URL || "").trim();
  if (!raw) return true;
  let hostname = "";
  try {
    hostname = new URL(raw).hostname.toLowerCase();
  } catch {
    return true;
  }
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "0.0.0.0") return true;
  if (hostname.startsWith("10.")) return true;
  if (hostname.startsWith("192.168.")) return true;
  if (/^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)) return true;
  return false;
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
const runningOnVercel = Boolean(process.env.VERCEL);

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
    if (runningOnVercel && backendLooksPrivateOrLocal()) {
      // Prevent Vercel runtime DNS_HOSTNAME_RESOLVED_PRIVATE from localhost/private BACKEND_URL.
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
