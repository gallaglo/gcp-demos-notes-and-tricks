import type { NextConfig } from 'next'
import type { Configuration } from 'webpack'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: {
      allowedOrigins: [
        'localhost:8080',
        'localhost:3000',
        '.run.app'
      ],
      bodySizeLimit: '2mb'
    }
  },
  // This needs to be at the top level, not in experimental
  output: 'standalone',
  // File tracing configuration for better handling of environment variables
  outputFileTracing: true,
  outputFileTracingRoot: process.cwd(),
  // Original webpack configuration
  webpack: (config: Configuration) => {
    // Handle canvas externals
    if (config.externals) {
      config.externals = [...(Array.isArray(config.externals) ? config.externals : [config.externals]), 
        { canvas: 'canvas' }
      ];
    } else {
      config.externals = [{ canvas: 'canvas' }];
    }

    // Add fallbacks for Node.js modules used in API routes
    if (!config.resolve) {
      config.resolve = {};
    }

    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      path: false,
    };

    return config;
  },
};

export default nextConfig;