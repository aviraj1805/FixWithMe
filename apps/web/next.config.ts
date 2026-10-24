import type { NextConfig } from "next";

// Static export: the PWA is served from Cloudflare Pages and all dynamic logic lives in the
// FastAPI backend (see docs/blueprint.md §2). Cache Components needs a Node.js server, so it
// stays off for the static build.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
