import { siteConfig } from '@/lib/site';

export default function robots() {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/second-ai-brain-overview', '/second-ai-brain-overview.html'],
    },
    sitemap: `${siteConfig.url}/sitemap.xml`,
  };
}
