import Link from 'next/link';

export default function ArticleBody({ article }) {
  return (
    <article className="mx-auto max-w-[680px] px-6 py-16">
      <Link href="/knowledge" className="text-sm font-medium text-primary transition-colors hover:text-primary-hover">
        ← Назад к знаниям
      </Link>

      <header className="mt-8 border-b border-border pb-10">
        <div className="flex flex-wrap gap-2">
          {article.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-primary/20 bg-primary-light px-3 py-1 text-xs font-semibold text-primary"
            >
              {tag}
            </span>
          ))}
        </div>
        <h1 className="mt-6 text-4xl font-bold leading-tight text-text-primary md:text-5xl">
          {article.title}
        </h1>
        <p className="mt-6 text-lg leading-8 text-text-secondary">
          {article.excerpt}
        </p>
        <div className="mt-6 text-sm text-text-tertiary">
          {article.publishedAt} · {article.readingTime}
        </div>
      </header>

      <div className="mt-12 space-y-12">
        {article.sections.map((section) => (
          <section key={section.heading} className="space-y-5">
            <h2 className="text-2xl font-bold text-text-primary">{section.heading}</h2>
            {section.paragraphs?.map((paragraph) => (
              <p key={paragraph} className="text-base leading-8 text-text-secondary">
                {paragraph}
              </p>
            ))}
            {section.list?.length ? (
              <ul className="space-y-3 text-base leading-8 text-text-secondary">
                {section.list.map((item) => (
                  <li key={item} className="flex gap-3">
                    <span className="mt-3 h-2 w-2 flex-none rounded-full bg-primary" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </div>

      <div className="mt-16 rounded-[28px] border border-border bg-[#071616] p-8 text-white">
        <h2 className="text-2xl font-bold text-white">Second AI Brain</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-white/70">
          Управленческий дизайн, упакованный в AI. Продуманные циклы и ритуалы, которые делают руководителя сильнее каждую неделю.
        </p>
        <Link
          href="/second-ai-brain"
          className="mt-6 inline-flex rounded-full gradient-cta px-6 py-3 text-sm font-semibold text-white"
        >
          Узнать о продукте
        </Link>
      </div>
    </article>
  );
}
