import { Inter, Sora } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const sora = Sora({
  subsets: ['latin', 'cyrillic'],
  weight: ['600', '700', '800'],
  variable: '--font-sora',
  display: 'swap',
});

export const metadata = {
  title: 'svaib — AI-решения для бизнеса',
  description: 'Продуктовая AI-мастерская, создающая AI-решения для управления встречами',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" className={`${inter.variable} ${sora.variable}`}>
      <body className="font-body antialiased">
        {children}
      </body>
    </html>
  );
}
