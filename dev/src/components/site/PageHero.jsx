import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

function CtaLink({ cta, primary = false }) {
  if (!cta) return null;

  const className = primary
    ? 'inline-flex items-center gap-2 rounded-full gradient-cta px-6 py-3 text-sm font-semibold text-white shadow-lg transition-transform hover:-translate-y-0.5'
    : 'inline-flex items-center gap-2 rounded-full border border-white/15 px-6 py-3 text-sm font-semibold text-white/85 transition-colors hover:border-white/35 hover:text-white';

  return cta.external ? (
    <a href={cta.href} target="_blank" rel="noopener noreferrer" className={className}>
      {cta.label}
      <ArrowRight size={16} />
    </a>
  ) : (
    <Link href={cta.href} className={className}>
      {cta.label}
      <ArrowRight size={16} />
    </Link>
  );
}

export default function PageHero({ title, subtitle, primaryCta, secondaryCta, eyebrow }) {
  return (
    <section className="relative overflow-hidden bg-[#071616] text-white">
      <div className="absolute inset-0 opacity-20">
        <div className="absolute left-[-8rem] top-16 h-64 w-64 rounded-full border border-primary/40" />
        <div className="absolute right-[-4rem] top-20 h-52 w-52 rounded-full border border-white/10" />
        <div className="absolute bottom-0 left-1/3 h-48 w-48 rounded-full border border-primary/20" />
      </div>

      <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
        <div className="max-w-4xl">
          {eyebrow ? (
            <p className="mb-6 text-xs font-semibold uppercase tracking-[0.28em] text-primary/90">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="max-w-4xl text-4xl font-bold leading-tight text-white md:text-6xl">
            {title}
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-white/72 md:text-xl">
            {subtitle}
          </p>

          {(primaryCta || secondaryCta) && (
            <div className="mt-10 flex flex-wrap gap-4">
              <CtaLink cta={primaryCta} primary />
              <CtaLink cta={secondaryCta} />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
