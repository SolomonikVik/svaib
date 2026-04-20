import { Inter, Montserrat, Fraunces } from 'next/font/google';
import './globals.css';
import SiteHeader from '@/components/site/SiteHeader';
import SiteFooter from '@/components/site/SiteFooter';
import { siteConfig } from '@/lib/site';

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const montserrat = Montserrat({
  subsets: ['latin', 'cyrillic'],
  weight: ['500', '600', '700', '800'],
  variable: '--font-montserrat',
  display: 'swap',
});

const fraunces = Fraunces({
  subsets: ['latin'],
  weight: ['700'],
  style: ['italic'],
  variable: '--font-fraunces',
  display: 'swap',
});

export const metadata = {
  metadataBase: new URL(siteConfig.url),
  title: siteConfig.title,
  description: siteConfig.description,
  openGraph: {
    title: siteConfig.title,
    description: siteConfig.description,
    url: siteConfig.url,
    siteName: siteConfig.name,
    locale: 'ru_RU',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: siteConfig.title,
    description: siteConfig.description,
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" className={`${inter.variable} ${montserrat.variable} ${fraunces.variable}`}>
      <body className="font-body antialiased">
        <div className="min-h-screen bg-background">
          <SiteHeader />
          <main>{children}</main>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
