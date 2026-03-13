import PageHero from '@/components/site/PageHero';
import SectionShell from '@/components/site/SectionShell';
import { archivePageContent } from '@/data/siteContent';
import { buildMetadata } from '@/lib/site';

export const metadata = buildMetadata({
  title: 'Archive',
  description: archivePageContent.hero.subtitle,
  path: '/archive',
});

export default function ArchivePage() {
  return (
    <>
      <PageHero {...archivePageContent.hero} />

      <SectionShell>
        <div className="grid gap-6 md:grid-cols-2">
          {archivePageContent.cards.map((card) => (
            <a
              key={card.href}
              href={card.href}
              className="rounded-[28px] border border-border bg-white p-8 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
            >
              <span className="rounded-full border border-primary/20 bg-primary-light px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                Исторический артефакт
              </span>
              <h2 className="mt-6 text-3xl font-bold text-text-primary">{card.title}</h2>
              <p className="mt-4 text-base leading-8 text-text-secondary">{card.subtitle}</p>
            </a>
          ))}
        </div>
      </SectionShell>
    </>
  );
}

