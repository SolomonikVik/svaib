import Link from 'next/link';
import { Menu } from 'lucide-react';
import { siteNavigation } from '@/data/siteContent';

function Logo() {
  return (
    <span className="font-display text-2xl font-extrabold tracking-[-0.02em] leading-none">
      <span className="text-white">sv</span>
      <span className="text-accent">ai</span>
      <span className="text-white">b</span>
      <span className="text-accent">.</span>
    </span>
  );
}

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink/95 text-white backdrop-blur">
      <div className="h-1 bg-primary" />
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="transition-opacity hover:opacity-80" aria-label="svaib">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {siteNavigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-white/70 transition-colors hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <details className="details-reset relative md:hidden">
          <summary className="flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-full border border-white/15 text-white/80 transition-colors hover:border-white/30 hover:text-white">
            <Menu size={18} />
          </summary>
          <div className="absolute right-0 top-12 w-64 rounded-2xl border border-white/10 bg-ink p-3 shadow-2xl">
            <nav className="flex flex-col">
              {siteNavigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-xl px-4 py-3 text-sm font-medium text-white/80 transition-colors hover:bg-white/5 hover:text-white"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </details>
      </div>
    </header>
  );
}

