import Hero from '@/components/Hero';
import Architecture from '@/components/Architecture';
import CTA from '@/components/CTA';
import Footer from '@/components/Footer';

export default function Home() {
  return (
    <main className="min-h-screen">
      <Hero />
      <Architecture />
      <CTA />
      <Footer />
    </main>
  );
}
