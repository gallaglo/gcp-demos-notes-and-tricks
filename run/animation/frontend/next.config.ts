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
  output: 'standalone',
  // Add API rewrites to proxy backend requests
  async rewrites() {
    return [
      {
        source: '/api/chat',
        destination: `${process.env.MCP_SERVER_URL || 'http://localhost:8000'}/api/chat`,
      },
    ];
  },
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