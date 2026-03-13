import PageHero from '@/components/site/PageHero';
import SectionShell from '@/components/site/SectionShell';
import { labContent } from '@/data/siteContent';
import { buildMetadata } from '@/lib/site';

export const metadata = buildMetadata({
  title: 'Lab',
  description: labContent.hero.subtitle,
  path: '/lab',
});

export default function LabPage() {
  return (
    <>
      <PageHero {...labContent.hero} />

      <SectionShell title={labContent.author.title}>
        <div className="max-w-4xl space-y-5">
          {labContent.author.paragraphs.map((paragraph) => (
            <p key={paragraph} className="text-lg leading-8 text-text-secondary">
              {paragraph}
            </p>
          ))}
        </div>
      </SectionShell>

      <SectionShell title={labContent.cringe.title} muted>
        <div className="rounded-[32px] bg-[#071616] p-8 text-white md:p-12">
          <div className="max-w-4xl space-y-6">
            {labContent.cringe.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-lg leading-8 text-white/78">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </SectionShell>

      <SectionShell title={labContent.lab.title}>
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            {labContent.lab.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-lg leading-8 text-text-secondary">
                {paragraph}
              </p>
            ))}
          </div>

          <div className="grid gap-4 rounded-[28px] border border-border bg-white p-6 shadow-sm">
            <div className="rounded-[22px] border border-border bg-background px-5 py-4 text-base font-medium text-text-primary">
              Лаборатория строит помощников
            </div>
            <div className="rounded-[22px] border border-border bg-background px-5 py-4 text-base font-medium text-text-primary">
              Помощники ускоряют продукт и контент
            </div>
            <div className="rounded-[22px] border border-border bg-background px-5 py-4 text-base font-medium text-text-primary">
              Клиенты дают обратную связь, лаборатория совершенствуется
            </div>
          </div>
        </div>
      </SectionShell>

      <SectionShell title={labContent.values.title} muted>
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {labContent.values.items.map((item) => (
            <article key={item.title} className="rounded-[28px] border border-border bg-white p-6 shadow-sm">
              <h3 className="text-xl font-bold text-text-primary">{item.title}</h3>
              <p className="mt-4 text-base leading-7 text-text-secondary">{item.description}</p>
            </article>
          ))}
        </div>
      </SectionShell>

      <SectionShell title={labContent.stage.title}>
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <p className="text-lg leading-8 text-text-secondary">{labContent.stage.text}</p>

          <div className="rounded-[28px] border border-border bg-white p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Ссылки</p>
            <div className="mt-5 space-y-4">
              {labContent.links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-base font-medium text-text-primary transition-colors hover:text-primary"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </SectionShell>
    </>
  );
}

