import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API proxying is handled by app/api/[...path]/route.ts at runtime,
  // which reads NEXT_PUBLIC_API_URL live on every request instead of
  // baking the URL in at build time (which caused the connection errors).
};

export default nextConfig;
