import Header from '@/components/Header';
import Hero from '@/components/Hero';
import Architecture from '@/components/Architecture';
import CTA from '@/components/CTA';
import Footer from '@/components/Footer';

export default function Home() {
  return (
    <main className="min-h-screen">
      <Header />
      <Hero />
      <Architecture />
      <CTA />
      <Footer />
    </main>
  );
}
