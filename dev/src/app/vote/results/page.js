'use client';

import { useState, useEffect } from 'react';
import { Clock, Check, CheckCircle, RefreshCw } from 'lucide-react';

export default function ResultsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadResults();
  }, []);

  async function loadResults() {
    // Сначала получаем сессию
    const sessionRes = await fetch('/api/vote/sessions');
    const sessionData = await sessionRes.json();

    if (!sessionData.session) {
      setLoading(false);
      return;
    }

    // Получаем результаты
    const res = await fetch(`/api/vote/results?session_id=${sessionData.session.id}`);
    const results = await res.json();

    setData({ session: sessionData.session, ...results });
    setLoading(false);
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  }

  if (!data?.session) {
    return (
      <div className="text-center py-12">
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-4">Нет активной сессии</h1>
        <p className="text-gray-500">Результаты появятся после завершения голосования</p>
      </div>
    );
  }

  // Голосование не завершено
  if (data.status !== 'completed') {
    return (
      <div className="text-center py-12">
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-4">{data.session.name}</h1>
        <Clock className="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-500 mb-6">Голосование ещё не завершено</p>

        <div className="bg-white rounded-xl p-6 max-w-md mx-auto border border-gray-200">
          <div className="text-sm text-gray-500 mb-2">Проголосовало</div>
          <div className="text-3xl font-bold text-gray-800 mb-4">{data.progress.voted} / {data.progress.total}</div>

          <div className="space-y-2">
            {data.participants?.map(p => (
              <div key={p.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{p.name}</span>
                {p.has_voted
                  ? <Check className="w-4 h-4 text-[#00B4A6]" />
                  : <Clock className="w-4 h-4 text-gray-400" />
                }
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={loadResults}
          className="mt-6 px-6 py-3 bg-[#00B4A6] text-white rounded-xl font-medium hover:bg-[#008B7F] transition flex items-center gap-2 mx-auto"
        >
          <RefreshCw className="w-5 h-5" /> Обновить
        </button>
      </div>
    );
  }

  // Результаты готовы
  const { participants, projects, cells } = data;

  return (
    <div>
      <div className="text-center mb-8">
        <h1 className="font-heading text-2xl font-bold text-gray-800">{data.session.name}</h1>
        <p className="text-[#00B4A6] font-medium mt-2 flex items-center justify-center gap-2">
          <CheckCircle className="w-5 h-5" /> Голосование завершено
        </p>
      </div>

      {/* Топ-3 */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {projects.slice(0, 3).map((project, i) => {
          const medals = ['🥇', '🥈', '🥉'];
          const bgColors = ['bg-yellow-50 border-yellow-200', 'bg-gray-50 border-gray-200', 'bg-orange-50 border-orange-200'];

          return (
            <div key={project.id} className={`${bgColors[i]} border rounded-xl p-4 text-center`}>
              <div className="text-3xl mb-2">{medals[i]}</div>
              <div className="font-heading font-semibold text-gray-800">{project.name}</div>
              <div className="text-2xl font-bold text-[#00B4A6] mt-2">{project.totalScore} баллов</div>
            </div>
          );
        })}
      </div>

      {/* Шахматка */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600 border-b sticky left-0 bg-gray-50 z-10 min-w-[40px]">#</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 border-b sticky left-[40px] bg-gray-50 z-10 min-w-[150px]">Название</th>
                {participants.map(p => (
                  <th key={p.id} className="px-3 py-3 text-center border-b min-w-[80px]">
                    <div className="font-medium text-gray-800 text-sm">{p.name}</div>
                    <div className="text-xs text-gray-400">{p.position} ({p.weight})</div>
                  </th>
                ))}
                <th className="px-4 py-3 text-center font-medium text-gray-600 border-b bg-[#F0FDFB]">Итого</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project, i) => {
                const isTopThree = i < 3;
                const rowBg = isTopThree ? 'bg-[#F0FDFB]' : (i % 2 === 0 ? 'bg-white' : 'bg-gray-50');
                const stickyBg = isTopThree ? 'bg-[#F0FDFB]' : (i % 2 === 0 ? 'bg-white' : 'bg-gray-50');

                return (
                  <tr key={project.id} className={rowBg}>
                    <td className={`px-4 py-3 border-b sticky left-0 z-10 ${stickyBg} ${isTopThree ? 'text-[#00B4A6] font-bold' : 'text-gray-400'}`}>
                      {i + 1}
                    </td>
                    <td className={`px-4 py-3 border-b sticky left-[40px] z-10 ${stickyBg}`}>
                      <div className={isTopThree ? 'font-bold text-gray-900' : 'font-medium text-gray-800'}>{project.name}</div>
                      {project.description && (
                        <div className="text-xs text-gray-500">{project.description}</div>
                      )}
                    </td>
                    {participants.map(p => {
                      const votes = cells[project.id]?.[p.id] || 0;
                      return (
                        <td key={p.id} className="px-3 py-3 text-center border-b">
                          {votes > 0 && (
                            <span className={`inline-block w-8 h-8 rounded-lg flex items-center justify-center font-bold ${
                              votes === 2 ? 'bg-[#00B4A6] text-white' : 'bg-[#E0F7F5] text-[#00B4A6]'
                            }`}>
                              {votes}
                            </span>
                          )}
                        </td>
                      );
                    })}
                    <td className="px-4 py-3 text-center border-b bg-[#F0FDFB]">
                      <span className={`font-bold text-[#00B4A6] ${isTopThree ? 'text-xl' : 'text-lg'}`}>{project.totalScore}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Легенда */}
      <div className="mt-4 flex items-center justify-center gap-6 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <span className="inline-block w-6 h-6 rounded bg-[#E0F7F5] text-[#00B4A6] text-center font-bold text-xs leading-6">1</span>
          <span>1 голос</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-6 h-6 rounded bg-[#00B4A6] text-white text-center font-bold text-xs leading-6">2</span>
          <span>2 голоса</span>
        </div>
        <div className="text-gray-400">Итого = голоса × вес участника</div>
      </div>
    </div>
  );
}
