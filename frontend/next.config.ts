// =============================================================================
// Next.js Configuration for Cortex frontend
// =============================================================================

import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Enable React strict mode for development warnings
  reactStrictMode: true,

  // All API traffic routes through the local backend only
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
