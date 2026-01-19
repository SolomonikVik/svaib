export default function CTA() {
  return (
    <section className="py-24 px-6 bg-gradient-to-br from-primary-subtle via-white to-accent-light">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl md:text-5xl font-bold text-text-primary mb-6 font-heading">
          Хотите навести порядок в управлении?
        </h2>
        <p className="text-xl text-text-secondary mb-8 max-w-2xl mx-auto">
          Обсудим ваш хаос и подскажем, как построить систему регулярного AI-менеджмента
        </p>
        <a
          href="https://t.me/solomonikvik"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block gradient-cta text-white px-8 py-4 rounded-lg font-semibold text-lg transition-all hover:shadow-xl hover:scale-105"
        >
          Навести порядок
        </a>
      </div>
    </section>
  );
}
