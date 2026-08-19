import type { NextConfig } from "next";

const outputMode = process.env.NEXT_OUTPUT_MODE;
const isStaticExport = outputMode === "export";
const usePollingFileWatcher = process.env.NEXT_DEV_POLLING === "1";

const nextConfig: NextConfig = {
  compress: true,
  distDir: process.env.NEXT_DIST_DIR || ".next",
  output:
    outputMode === "standalone"
      ? "standalone"
      : isStaticExport
        ? "export"
        : undefined,
  poweredByHeader: false,
  trailingSlash: isStaticExport,
  transpilePackages: ["@prepvilla/types"],
  watchOptions: usePollingFileWatcher
    ? {
        pollIntervalMs: 300,
      }
    : undefined,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  images: {
    // Local Docker browsers can reach localhost:9500, but the Next.js
    // server runs in a different container and cannot proxy that hostname.
    unoptimized: isStaticExport || process.env.NODE_ENV !== "production",
    remotePatterns: [
      {
        hostname: 'localhost',
        port: '8500',
        protocol: 'http',
      },
      {
        hostname: '127.0.0.1',
        port: '8500',
        protocol: 'http',
      },
      {
        hostname: 'localhost',
        port: '9500',
        protocol: 'http',
      },
      {
        hostname: '127.0.0.1',
        port: '9500',
        protocol: 'http',
      },
      {
        hostname: 'prepvilla.info',
        protocol: 'https',
      },
      {
        hostname: 'dev.prepvilla.info',
        protocol: 'https',
      },
      {
        hostname: 'media.prepvilla.info',
        protocol: 'https',
      },
      {
        hostname: 'media.dev.prepvilla.info',
        protocol: 'https',
      },
    ],
  },
};

export default nextConfig;
