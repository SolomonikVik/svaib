/** @type {import('next').NextConfig} */
const nextConfig = {
  // Оставляем архив доступным через /archive/
  async rewrites() {
    return [
      {
        source: '/archive/:path*',
        destination: '/archive/:path*',
      },
    ];
  },
};

export default nextConfig;
