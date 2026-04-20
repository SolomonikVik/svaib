export default function SectionShell({
  title,
  description,
  children,
  className = '',
  muted = false,
  kicker,
  accentDot = false,
}) {
  return (
    <section className={muted ? `bg-primary-subtle ${className}` : className}>
      <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        {(title || description || kicker) && (
          <div className="mb-12 max-w-3xl">
            {kicker && (
              <p className="mb-5 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-primary-dark">
                {kicker}
              </p>
            )}
            {title && (
              <h2 className="font-display text-3xl font-bold leading-[1.05] tracking-[-0.025em] text-ink md:text-5xl">
                {title}
                {accentDot && <span className="text-accent">.</span>}
              </h2>
            )}
            {description && (
              <p className="mt-5 text-lg leading-8 text-ink-soft">
                {description}
              </p>
            )}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}
