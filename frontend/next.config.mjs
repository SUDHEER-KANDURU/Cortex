/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three', '@react-three/fiber', '@react-three/drei'],

  // Disable webpack cache symlinks — required when project lives inside OneDrive
  // OneDrive's virtual filesystem breaks Node's readlink on Windows
  webpack: (config) => {
    config.cache = false;
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
