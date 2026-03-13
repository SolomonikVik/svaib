export default function SectionShell({
  title,
  description,
  children,
  className = '',
  muted = false,
}) {
  return (
    <section className={muted ? `bg-[#F0FDFB] ${className}` : className}>
      <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        {(title || description) && (
          <div className="mb-10 max-w-3xl">
            {title && <h2 className="text-3xl font-bold text-text-primary md:text-4xl">{title}</h2>}
            {description && (
              <p className="mt-4 text-lg leading-8 text-text-secondary">
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

