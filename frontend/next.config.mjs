/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three', '@react-three/fiber', '@react-three/drei'],

  // Disable webpack cache — required when project lives inside OneDrive
  webpack: (config, { isServer }) => {
    config.cache = false;
    // Disable webpack's resolve.symlinks to prevent TypeScript path assertion
    // failures caused by OneDrive reparse points and junctions on Windows.
    config.resolve = {
      ...config.resolve,
      symlinks: false,
    };

    if (!isServer) {
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...(config.optimization.splitChunks?.cacheGroups ?? {}),
          three: {
            test: /[\\/]node_modules[\\/](three|@react-three)[\\/]/,
            name: 'three-vendor',
            chunks: 'async',
            priority: 30,
            enforce: true,
          },
        },
      };
    }

    return config;
  },

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
