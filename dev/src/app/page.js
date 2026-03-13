import Link from 'next/link';
import { ArrowRight, Brain, FlaskConical, Newspaper } from 'lucide-react';
import PageHero from '@/components/site/PageHero';
import SectionShell from '@/components/site/SectionShell';
import ArticleCard from '@/components/site/ArticleCard';
import { getKnowledgeArticles } from '@/data/knowledgeArticles';
import { homeContent } from '@/data/siteContent';
import { buildMetadata } from '@/lib/site';

export const metadata = buildMetadata({
  description: homeContent.hero.subtitle,
  path: '/',
});

const directionIcons = [Brain, FlaskConical, Newspaper];

export default function Home() {
  const articles = getKnowledgeArticles();

  return (
    <>
      <PageHero {...homeContent.hero} />

      <SectionShell title={homeContent.directions.title}>
        <div className="grid gap-6 md:grid-cols-3">
          {homeContent.directions.items.map((item, index) => {
            const Icon = directionIcons[index];

            return (
              <article
                key={item.title}
                className="rounded-[28px] border border-border bg-white p-8 shadow-sm transition-transform hover:-translate-y-1 hover:shadow-lg"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-light text-primary">
                  <Icon size={22} />
                </div>
                <p className="mt-6 text-xs font-semibold uppercase tracking-[0.24em] text-text-tertiary">
                  {item.label}
                </p>
                <h3 className="mt-3 text-2xl font-bold text-text-primary">{item.title}</h3>
                <p className="mt-4 text-base leading-8 text-text-secondary">{item.description}</p>
              </article>
            );
          })}
        </div>
      </SectionShell>

      <SectionShell title={homeContent.problemTeaser.title} muted>
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.9fr]">
          <p className="text-lg leading-8 text-text-secondary">
            {homeContent.problemTeaser.text}
          </p>
          <Link
            href={homeContent.problemTeaser.href}
            className="inline-flex h-fit items-center gap-2 rounded-full border border-primary/20 bg-white px-6 py-3 text-sm font-semibold text-primary transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.problemTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell title={homeContent.layersTeaser.title}>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1fr]">
          {homeContent.layersTeaser.items.map((item) => (
            <article key={item.title} className="rounded-[28px] border border-border bg-white p-8 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">
                {item.label}
              </p>
              <h3 className="mt-4 text-2xl font-bold text-text-primary">{item.title}</h3>
              <p className="mt-4 text-base leading-8 text-text-secondary">{item.description}</p>
            </article>
          ))}
        </div>
        <div className="mt-8">
          <Link
            href={homeContent.layersTeaser.href}
            className="inline-flex items-center gap-2 rounded-full border border-primary/20 px-6 py-3 text-sm font-semibold text-primary transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.layersTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell title={homeContent.authorTeaser.title} muted>
        <div className="grid gap-8 lg:grid-cols-[1.35fr_0.85fr]">
          <p className="text-lg leading-8 text-text-secondary">
            {homeContent.authorTeaser.text}
          </p>
          <Link
            href={homeContent.authorTeaser.href}
            className="inline-flex h-fit items-center gap-2 rounded-full border border-primary/20 bg-white px-6 py-3 text-sm font-semibold text-primary transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.authorTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell title={homeContent.knowledgeTeaser.title} description={homeContent.knowledgeTeaser.text}>
        <div className="grid gap-6 lg:grid-cols-3">
          {articles.map((article) => (
            <ArticleCard key={article.slug} article={article} />
          ))}
        </div>
      </SectionShell>

      <section className="border-y border-primary/10 bg-primary-light/50">
        <div className="mx-auto max-w-6xl px-6 py-8 text-center">
          <p className="text-lg font-medium text-text-primary md:text-xl">
            {homeContent.missionStrip}
          </p>
        </div>
      </section>

      <SectionShell>
        <div className="rounded-[32px] bg-[#071616] px-8 py-12 text-white md:px-12">
          <h2 className="text-3xl font-bold text-white md:text-4xl">
            {homeContent.finalCta.title}
          </h2>
          <a
            href={homeContent.finalCta.href}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 inline-flex items-center gap-2 rounded-full gradient-cta px-6 py-3 text-sm font-semibold text-white"
          >
            {homeContent.finalCta.label}
            <ArrowRight size={16} />
          </a>
        </div>
      </SectionShell>
    </>
  );
}
