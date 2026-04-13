import type { NextConfig } from "next";

const backend = process.env.BACKEND_URL || "http://127.0.0.1:8010";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
