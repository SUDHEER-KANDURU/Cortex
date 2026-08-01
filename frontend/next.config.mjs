/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Compress responses with gzip — large improvement on first-load HTML/JS
  compress: true,

  // Don't advertise Next.js in response headers
  poweredByHeader: false,

  // Three.js and @react-three need to be transpiled by Next.js / SWC
  transpilePackages: ['three', '@react-three/fiber', '@react-three/drei'],

  // Disable webpack cache — required when project lives inside OneDrive
  // (OneDrive's reparse points corrupt the cache on Windows)
  webpack: (config, { isServer }) => {
    config.cache = false;

    // Disable symlinks resolution — prevents TypeScript path failures
    // caused by OneDrive junctions on Windows
    config.resolve = {
      ...config.resolve,
      symlinks: false,
    };

    if (!isServer) {
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...(config.optimization.splitChunks?.cacheGroups ?? {}),

          // Three.js is ~1.5 MB — keep it in its own async chunk so it
          // never blocks the initial page paint
          three: {
            test: /[\\/]node_modules[\\/](three|@react-three)[\\/]/,
            name: 'three-vendor',
            chunks: 'async',
            priority: 30,
            enforce: true,
          },

          // framer-motion is pulled in by JourneyNav (dead code) but guard
          // anyway — keep it async so it doesn't land in the main bundle
          framerMotion: {
            test: /[\\/]node_modules[\\/]framer-motion[\\/]/,
            name: 'framer-motion-vendor',
            chunks: 'async',
            priority: 25,
            enforce: true,
          },

          // mermaid is large — keep it async
          mermaid: {
            test: /[\\/]node_modules[\\/]mermaid[\\/]/,
            name: 'mermaid-vendor',
            chunks: 'async',
            priority: 25,
            enforce: true,
          },
        },
      };
    }

    return config;
  },

  // Proxy all /api/v1/* calls to the FastAPI backend so no CORS issues
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
