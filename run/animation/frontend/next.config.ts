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
    // Make sure we have a valid endpoint with a fallback
    const endpoint = process.env.LANGGRAPH_ENDPOINT || 'http://agent:8080';

    // Add log to see what endpoint is being used
    console.log("Next.js API rewrite using endpoint:", endpoint);
    
    return [
      {
        source: '/api/:path*',
        destination: `${endpoint}/:path*`, // Proxy to the agent service
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