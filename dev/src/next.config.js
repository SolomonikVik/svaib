/** @type {import('next').NextConfig} */
const nextConfig = {
  // Оставляем архив доступным через /archive/
  async rewrites() {
    return [
      {
        source: '/second-ai-brain-overview',
        destination: '/second-ai-brain-overview.html',
      },
      {
        source: '/archive/:path*',
        destination: '/archive/:path*',
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/second-ai-brain-overview',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
      {
        source: '/second-ai-brain-overview.html',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
