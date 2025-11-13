export default function Hero() {
  return (
    <section className="relative flex items-center justify-center px-6 pt-28 pb-16 bg-gradient-to-br from-primary-subtle via-white to-accent-light">
      <div className="max-w-5xl mx-auto text-center">
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 gradient-text leading-tight">
          AI-система управления,
          <br />
          которая помнит всё
        </h1>
        <p className="text-xl md:text-2xl text-text-secondary mb-8 max-w-3xl mx-auto font-medium">
          Структурированные встречи + AI-ассистент =<br />
          наведут порядок в управлении за вас
        </p>
        <a
          href="https://t.me/NikMer"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block gradient-cta text-white px-6 py-3 rounded-lg font-semibold text-base shadow-lg hover:shadow-xl transition-all hover:-translate-y-1 hover:scale-105"
        >
          Обсудить запуск
        </a>
      </div>
    </section>
  );
}
