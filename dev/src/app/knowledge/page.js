import PageHero from '@/components/site/PageHero';
import SectionShell from '@/components/site/SectionShell';
import ArticleCard from '@/components/site/ArticleCard';
import { getKnowledgeArticles } from '@/data/knowledgeArticles';
import { knowledgePageContent } from '@/data/siteContent';
import { buildMetadata } from '@/lib/site';

export const metadata = buildMetadata({
  title: 'Knowledge',
  description: knowledgePageContent.hero.subtitle,
  path: '/knowledge',
});

export default function KnowledgePage() {
  const articles = getKnowledgeArticles();

  return (
    <>
      <PageHero {...knowledgePageContent.hero} />

      <SectionShell>
        <div className="grid gap-6 lg:grid-cols-3">
          {articles.map((article) => (
            <ArticleCard key={article.slug} article={article} />
          ))}
        </div>
      </SectionShell>
    </>
  );
}

