import type { NextConfig } from "next";

/** Base URL for FastAPI (phase6): /ui-api/*, /health/detailed. No trailing slash. Not a Streamlit URL. */
function backendOrigin(): string {
  const raw = process.env.BACKEND_URL || "http://127.0.0.1:8010";
  return raw.replace(/\/+$/, "");
}

const nextConfig: NextConfig = {
  async rewrites() {
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
