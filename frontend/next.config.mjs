/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three', '@react-three/fiber', '@react-three/drei'],

  // Disable webpack cache symlinks — required when project lives inside OneDrive
  // OneDrive's virtual filesystem breaks Node's readlink on Windows
  webpack: (config, { isServer }) => {
    config.cache = false;

    // Move Three.js + R3F into a dedicated async chunk so the main bundle stays small
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
