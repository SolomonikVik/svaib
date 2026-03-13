export default function ScenarioCard({ scenario }) {
  return (
    <article className="rounded-[32px] border border-white/10 bg-[#101616] p-6 text-white shadow-2xl">
      <h3 className="text-2xl font-bold text-white">{scenario.title}</h3>
      <div className="mt-6 grid gap-6 md:grid-cols-[1.15fr_0.8fr_1.15fr]">
        <div className="rounded-[24px] border border-primary/30 bg-white/[0.02] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Вход</p>
          <pre className="mt-4 whitespace-pre-wrap font-mono text-sm leading-7 text-white/86">
            {scenario.input}
          </pre>
        </div>

        <div className="flex flex-col justify-center rounded-[24px] border border-white/8 bg-white/[0.03] p-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Обработка</p>
          <p className="mt-4 text-sm leading-7 text-white/70">{scenario.process}</p>
        </div>

        <div className="rounded-[24px] border border-white/8 bg-[#0E2222] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Результат</p>
          <pre className="mt-4 whitespace-pre-wrap font-mono text-sm leading-7 text-white/88">
            {scenario.output}
          </pre>
        </div>
      </div>
    </article>
  );
}

