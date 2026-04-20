import Link from 'next/link';
import { footerNavigation } from '@/data/siteContent';

export default function SiteFooter() {
  return (
    <footer className="border-t border-border bg-ink text-white">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr]">
          <div className="space-y-4">
            <p className="font-display text-2xl font-extrabold tracking-[-0.02em] leading-none">
              <span className="text-white">sv</span>
              <span className="text-accent">ai</span>
              <span className="text-white">b</span>
              <span className="text-accent">.</span>
            </p>
            <p className="max-w-xl text-sm leading-7 text-white/65">
              Управленческий дизайн, упакованный в AI. Данные у вас, методология у нас.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {footerNavigation.map((item) =>
              item.external ? (
                <a
                  key={item.href}
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-white/70 transition-colors hover:text-white"
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-sm text-white/70 transition-colors hover:text-white"
                >
                  {item.label}
                </Link>
              )
            )}
          </div>
        </div>

        <div className="mt-10 border-t border-white/10 pt-6 text-sm text-white/45">
          © 2025-2026 svaib
        </div>
      </div>
    </footer>
  );
}
