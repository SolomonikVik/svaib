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
      <PageHero
        eyebrow="01 · Second AI Brain"
        title={
          <>
            Second AI Brain — <span className="font-accent italic font-bold text-accent">управленческий</span> дизайн, упакованный в AI
          </>
        }
        subtitle={homeContent.hero.subtitle}
        primaryCta={homeContent.hero.primaryCta}
        secondaryCta={homeContent.hero.secondaryCta}
        accentDot
      />

      <SectionShell
        kicker="02 · Три направления"
        title="Продукт, лаборатория и публикации"
      >
        <div className="grid gap-6 md:grid-cols-3">
          {homeContent.directions.items.map((item, index) => {
            const Icon = directionIcons[index];

            return (
              <article
                key={item.title}
                className="rounded-[20px] border border-border bg-white p-9 transition-transform hover:-translate-y-1 hover:shadow-lg"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-light text-primary-dark">
                  <Icon size={22} />
                </div>
                <p className="mt-7 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">
                  {item.label}
                </p>
                <h3 className="font-display mt-3 text-2xl font-bold tracking-[-0.015em] text-ink leading-tight">
                  {item.title}
                </h3>
                <p className="mt-4 text-[15px] leading-7 text-ink-soft">{item.description}</p>
              </article>
            );
          })}
        </div>
      </SectionShell>

      <SectionShell
        kicker="03 · Проблема"
        title={
          <>
            Почему AI <span className="font-accent italic font-bold text-accent">не проникает</span> в управление
          </>
        }
        muted
      >
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.9fr]">
          <p className="text-lg leading-8 text-ink-soft">
            {homeContent.problemTeaser.text}
          </p>
          <Link
            href={homeContent.problemTeaser.href}
            className="inline-flex h-fit items-center gap-2 rounded-full border border-primary/25 bg-white px-6 py-3 text-sm font-semibold text-primary-dark transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.problemTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell
        kicker="04 · Архитектура"
        title={
          <>
            Как устроен <span className="font-accent italic font-bold text-accent">Second AI Brain</span>
          </>
        }
      >
        <div className="grid gap-6 lg:grid-cols-3">
          {homeContent.layersTeaser.items.map((item) => (
            <article key={item.title} className="rounded-[20px] border border-border bg-white p-9">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-primary-dark">
                {item.label}
              </p>
              <h3 className="font-display mt-4 text-2xl font-bold tracking-[-0.015em] text-ink leading-tight">
                {item.title}
              </h3>
              <p className="mt-4 text-[15px] leading-7 text-ink-soft">{item.description}</p>
            </article>
          ))}
        </div>
        <div className="mt-10">
          <Link
            href={homeContent.layersTeaser.href}
            className="inline-flex items-center gap-2 rounded-full border border-primary/25 px-6 py-3 text-sm font-semibold text-primary-dark transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.layersTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell
        kicker="05 · Автор"
        title="100 недель кринжа"
        muted
      >
        <div className="grid gap-8 lg:grid-cols-[1.35fr_0.85fr]">
          <p className="text-lg leading-8 text-ink-soft">
            {homeContent.authorTeaser.text}
          </p>
          <Link
            href={homeContent.authorTeaser.href}
            className="inline-flex h-fit items-center gap-2 rounded-full border border-primary/25 bg-white px-6 py-3 text-sm font-semibold text-primary-dark transition-colors hover:border-primary hover:bg-primary-light"
          >
            {homeContent.authorTeaser.label}
            <ArrowRight size={16} />
          </Link>
        </div>
      </SectionShell>

      <SectionShell
        kicker="06 · Knowledge Hub"
        title={
          <>
            <span className="font-accent italic font-bold text-accent">Практические</span> знания об AI в управлении
          </>
        }
        description={homeContent.knowledgeTeaser.text}
      >
        <div className="grid gap-6 lg:grid-cols-3">
          {articles.map((article) => (
            <ArticleCard key={article.slug} article={article} />
          ))}
        </div>
      </SectionShell>

      <section className="border-y border-primary/15 bg-primary-light/40">
        <div className="mx-auto max-w-6xl px-6 py-10 text-center">
          <p className="font-display text-xl font-medium tracking-[-0.01em] text-ink md:text-2xl">
            {homeContent.missionStrip}
            <span className="text-accent">.</span>
          </p>
        </div>
      </section>

      <SectionShell>
        <div className="rounded-[28px] bg-ink px-10 py-14 text-white md:px-14">
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-primary">
            07 · Запуск
          </p>
          <h2 className="font-display mt-5 max-w-2xl text-3xl font-bold tracking-[-0.025em] text-white md:text-5xl leading-[1.05]">
            Хотите попробовать Second AI Brain в <span className="font-accent italic font-bold text-accent">своём</span> бизнесе
            <span className="text-accent">?</span>
          </h2>
          <a
            href={homeContent.finalCta.href}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-10 inline-flex items-center gap-2 rounded-full bg-accent px-7 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            {homeContent.finalCta.label}
            <ArrowRight size={16} />
          </a>
        </div>
      </SectionShell>
    </>
  );
}
