import { getKnowledgeArticles } from '@/data/knowledgeArticles';
import { siteConfig } from '@/lib/site';

export default function sitemap() {
  const staticPages = ['/', '/second-ai-brain', '/lab', '/knowledge', '/archive'];
  const now = new Date();

  const staticEntries = staticPages.map((path) => ({
    url: `${siteConfig.url}${path === '/' ? '' : path}`,
    lastModified: now,
  }));

  const articleEntries = getKnowledgeArticles().map((article) => ({
    url: `${siteConfig.url}/knowledge/${article.slug}`,
    lastModified: new Date(article.publishedAt),
  }));

  return [...staticEntries, ...articleEntries];
}
