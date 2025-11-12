export default function CTA() {
  return (
    <section className="py-24 px-6 bg-gradient-to-br from-primary-subtle via-white to-accent-light">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl md:text-5xl font-bold text-text-primary mb-6 font-heading">
          Готовы структурировать свои встречи?
        </h2>
        <p className="text-xl text-text-secondary mb-8 max-w-2xl mx-auto">
          Обсудим ваши задачи и подберём решение под специфику вашего бизнеса
        </p>
        <a
          href="https://t.me/NikMer"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block gradient-cta text-white px-8 py-4 rounded-lg font-semibold text-lg transition-all hover:shadow-xl hover:scale-105"
        >
          Обсудить внедрение
        </a>
      </div>
    </section>
  );
}
