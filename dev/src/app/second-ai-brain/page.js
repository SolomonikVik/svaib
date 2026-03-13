import PageHero from '@/components/site/PageHero';
import SectionShell from '@/components/site/SectionShell';
import ScenarioCard from '@/components/site/ScenarioCard';
import { demoScenarios, secondAiBrainContent } from '@/data/siteContent';
import { buildMetadata } from '@/lib/site';

export const metadata = buildMetadata({
  title: 'Second AI Brain',
  description: secondAiBrainContent.hero.subtitle,
  path: '/second-ai-brain',
});

export default function SecondAiBrainPage() {
  return (
    <>
      <PageHero {...secondAiBrainContent.hero} />

      <SectionShell title={secondAiBrainContent.problem.title}>
        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.2fr]">
          <div className="rounded-[28px] border border-border bg-[#071616] p-8 text-white">
            <div className="space-y-4 text-xl leading-9 text-white/90">
              {secondAiBrainContent.problem.quotes.map((quote) => (
                <p key={quote} className="border-l-2 border-primary pl-5">
                  “{quote}”
                </p>
              ))}
            </div>
          </div>
          <p className="text-lg leading-8 text-text-secondary">
            {secondAiBrainContent.problem.text}
          </p>
        </div>
      </SectionShell>

      <SectionShell title={secondAiBrainContent.layers.title} muted>
        <div className="grid gap-6 lg:grid-cols-3">
          {secondAiBrainContent.layers.items.map((item) => (
            <article key={item.title} className="rounded-[28px] border border-border bg-white p-8 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">
                  Слой
                </span>
                <span className="text-4xl font-bold text-primary/20">{item.number}</span>
              </div>
              <h3 className="mt-6 text-2xl font-bold text-text-primary">{item.title}</h3>
              <p className="mt-4 text-base leading-8 text-text-secondary">{item.description}</p>
              <div className="mt-6 rounded-[22px] border border-primary/15 bg-primary-light/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                  Под капотом
                </p>
                <p className="mt-3 text-sm leading-7 text-text-secondary">{item.technical}</p>
              </div>
            </article>
          ))}
        </div>
      </SectionShell>

      <SectionShell title="Demo">
        <div className="space-y-6">
          {demoScenarios.map((scenario) => (
            <ScenarioCard key={scenario.title} scenario={scenario} />
          ))}
        </div>
      </SectionShell>

      <SectionShell
        title={secondAiBrainContent.implementation.title}
        description={secondAiBrainContent.implementation.intro}
        muted
      >
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {secondAiBrainContent.implementation.steps.map((step) => (
            <article key={step.title} className="rounded-[28px] border border-border bg-white p-8 shadow-sm">
              <h3 className="text-2xl font-bold text-text-primary">{step.title}</h3>
              <p className="mt-4 text-base leading-8 text-text-secondary">{step.description}</p>
            </article>
          ))}
        </div>
      </SectionShell>

      <SectionShell title={secondAiBrainContent.businessModel.title}>
        <div className="max-w-4xl">
          <p className="text-lg leading-8 text-text-secondary">
            {secondAiBrainContent.businessModel.intro}
          </p>
          <p className="mt-5 text-lg leading-8 text-text-secondary">
            {secondAiBrainContent.businessModel.outro}
          </p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <div className="rounded-[28px] border border-border bg-[#071616] p-8 text-white">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">
              {secondAiBrainContent.businessModel.leftTitle}
            </p>
            <ul className="mt-6 space-y-4 text-base leading-8 text-white/78">
              {secondAiBrainContent.businessModel.leftItems.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-[28px] border border-primary/20 bg-primary-light/60 p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">
              {secondAiBrainContent.businessModel.rightTitle}
            </p>
            <ul className="mt-6 space-y-4 text-base leading-8 text-text-secondary">
              {secondAiBrainContent.businessModel.rightItems.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
        </div>
      </SectionShell>

      <SectionShell title={secondAiBrainContent.audience.title} muted>
        <p className="max-w-4xl text-lg leading-8 text-text-secondary">
          {secondAiBrainContent.audience.text}
        </p>
      </SectionShell>

      <SectionShell>
        <div className="rounded-[32px] bg-[#071616] px-8 py-12 text-white md:px-12">
          <h2 className="text-3xl font-bold text-white md:text-4xl">
            {secondAiBrainContent.finalCta.title}
          </h2>
          <a
            href={secondAiBrainContent.finalCta.href}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 inline-flex rounded-full gradient-cta px-6 py-3 text-sm font-semibold text-white"
          >
            {secondAiBrainContent.finalCta.label}
          </a>
        </div>
      </SectionShell>
    </>
  );
}

