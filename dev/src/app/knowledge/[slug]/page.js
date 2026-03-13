import { notFound } from 'next/navigation';
import ArticleBody from '@/components/site/ArticleBody';
import { getKnowledgeArticle, getKnowledgeArticles } from '@/data/knowledgeArticles';
import { buildMetadata } from '@/lib/site';

export function generateStaticParams() {
  return getKnowledgeArticles().map((article) => ({ slug: article.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const article = getKnowledgeArticle(slug);

  if (!article) {
    return buildMetadata({
      title: 'Knowledge',
      path: '/knowledge',
    });
  }

  return buildMetadata({
    title: article.title,
    description: article.excerpt,
    path: `/knowledge/${article.slug}`,
  });
}

export default async function KnowledgeArticlePage({ params }) {
  const { slug } = await params;
  const article = getKnowledgeArticle(slug);

  if (!article) {
    notFound();
  }

  return <ArticleBody article={article} />;
}
