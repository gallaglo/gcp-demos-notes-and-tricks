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
  output: 'standalone', // Add this line
  webpack: (config: Configuration) => {
    if (config.externals) {
      config.externals = [...(Array.isArray(config.externals) ? config.externals : [config.externals]), 
        { canvas: 'canvas' }
      ];
    } else {
      config.externals = [{ canvas: 'canvas' }];
    }
    return config;
  },
};

export default nextConfig;