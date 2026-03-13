import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';

export default function ArticleCard({ article }) {
  return (
    <Link
      href={`/knowledge/${article.slug}`}
      className="group flex h-full flex-col rounded-[28px] border border-border bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
    >
      <div className="flex items-center justify-between text-xs font-medium uppercase tracking-[0.22em] text-text-tertiary">
        <span>{article.readingTime}</span>
        <ArrowUpRight size={16} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </div>
      <h3 className="mt-6 text-2xl font-bold text-text-primary">
        {article.title}
      </h3>
      <p className="mt-4 flex-1 text-base leading-7 text-text-secondary">
        {article.excerpt}
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        {article.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-primary/20 bg-primary-light px-3 py-1 text-xs font-semibold text-primary"
          >
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}

