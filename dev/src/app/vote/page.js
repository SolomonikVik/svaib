'use client';

import { useState, useEffect } from 'react';
import { POSITIONS } from '@/lib/supabase';
import { CheckCircle, Check } from 'lucide-react';

export default function VotePage() {
  const [session, setSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  const [votes, setVotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [voted, setVoted] = useState(false);

  useEffect(() => {
    loadSession();
  }, []);

  async function loadSession() {
    const res = await fetch('/api/vote/sessions');
    const data = await res.json();

    if (data.session) {
      setSession(data.session);
      setParticipants(data.session.vote_participants || []);
      setProjects((data.session.vote_projects || []).sort((a, b) => a.order_index - b.order_index));
    }
    setLoading(false);
  }

  const maxVotes = Math.ceil(projects.length / 2);
  const usedVotes = Object.values(votes).reduce((sum, v) => sum + v, 0);
  const remainingVotes = maxVotes - usedVotes;

  function handleVoteChange(projectId) {
    const current = votes[projectId] || 0;
    let next = current + 1;
    if (next > 2) next = 0;

    // Проверка лимита
    const newUsed = usedVotes - current + next;
    if (newUsed > maxVotes) {
      next = 0; // Сбрасываем если превышен лимит
    }

    setVotes({ ...votes, [projectId]: next });
  }

  async function handleSubmit() {
    if (!selectedParticipant) return;

    setSubmitting(true);

    const voteArray = Object.entries(votes)
      .filter(([_, v]) => v > 0)
      .map(([project_id, votes_given]) => ({ project_id, votes_given }));

    const res = await fetch('/api/vote/cast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        participant_id: selectedParticipant.id,
        votes: voteArray,
      }),
    });

    const data = await res.json();
    setSubmitting(false);

    if (data.success) {
      setVoted(true);
    } else {
      alert(data.error || 'Ошибка при голосовании');
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-4">Нет активной сессии</h1>
        <p className="text-gray-500">Попросите администратора создать сессию голосования</p>
      </div>
    );
  }

  if (session.status === 'draft') {
    return (
      <div className="text-center py-12">
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-4">Голосование ещё не началось</h1>
        <p className="text-gray-500">Администратор готовит сессию</p>
      </div>
    );
  }

  if (session.status === 'completed') {
    return (
      <div className="text-center py-12">
        <h1 className="font-heading text-2xl font-bold text-[#00B4A6] mb-4">Голосование завершено!</h1>
        <p className="text-gray-500 mb-6">Все участники проголосовали</p>
        <a href="/vote/results" className="inline-block bg-[#00B4A6] text-white px-6 py-3 rounded-xl font-medium hover:bg-[#008B7F] transition">
          Смотреть результаты →
        </a>
      </div>
    );
  }

  if (voted) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-16 h-16 mx-auto mb-4 text-[#00B4A6]" />
        <h1 className="font-heading text-2xl font-bold text-[#00B4A6] mb-4">Спасибо!</h1>
        <p className="text-gray-500">Ваш голос записан. Ожидаем остальных участников.</p>
      </div>
    );
  }

  // Шаг 1: Выбор участника
  if (!selectedParticipant) {
    const availableParticipants = participants.filter(p => !p.has_voted);

    return (
      <div>
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-2">{session.name}</h1>
        <p className="text-gray-500 mb-8">Выберите себя из списка</p>

        <div className="grid gap-3">
          {availableParticipants.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedParticipant(p)}
              className="bg-white border border-gray-200 rounded-xl p-4 text-left hover:border-[#00B4A6] hover:shadow-md transition"
            >
              <div className="font-medium text-gray-800">{p.name}</div>
              <div className="text-sm text-gray-500">{POSITIONS.find(pos => pos.value === p.position)?.label}</div>
            </button>
          ))}
        </div>

        {participants.filter(p => p.has_voted).length > 0 && (
          <div className="mt-8 pt-6 border-t">
            <p className="text-sm text-gray-400 mb-2">Уже проголосовали:</p>
            <div className="flex flex-wrap gap-2">
              {participants.filter(p => p.has_voted).map(p => (
                <span key={p.id} className="text-sm bg-[#E0F7F5] text-[#00B4A6] px-3 py-1 rounded-full inline-flex items-center gap-1">
                  {p.name} <Check className="w-3 h-3" />
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Шаг 2: Голосование
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-gray-800">{session.name}</h1>
          <p className="text-gray-500">Голосует: <span className="font-medium text-gray-700">{selectedParticipant.name}</span></p>
        </div>
        <button
          onClick={() => {
            setSelectedParticipant(null);
            setVotes({});
          }}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          ← Выбрать другого
        </button>
      </div>

      {/* Счётчик голосов */}
      <div className="bg-white rounded-xl p-4 mb-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-gray-600">Голосов осталось:</span>
          <span className={`text-2xl font-bold ${remainingVotes === 0 ? 'text-[#FF4D8D]' : 'text-[#00B4A6]'}`}>
            {remainingVotes} из {maxVotes}
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">Нажмите на проект: 0 → 1 → 2 → 0</p>
      </div>

      {/* Проекты */}
      <div className="grid gap-3 mb-8">
        {projects.map(project => {
          const v = votes[project.id] || 0;
          const bgColor = v === 0 ? 'bg-white' : v === 1 ? 'bg-[#E0F7F5]' : 'bg-[#00B4A6]';
          const textColor = v === 2 ? 'text-white' : 'text-gray-800';

          return (
            <button
              key={project.id}
              onClick={() => handleVoteChange(project.id)}
              className={`${bgColor} border border-gray-200 rounded-xl p-4 text-left transition hover:shadow-md`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className={`font-medium ${textColor}`}>{project.name}</div>
                  {project.description && (
                    <div className={`text-sm mt-1 ${v === 2 ? 'text-white/80' : 'text-gray-500'}`}>
                      {project.description}
                    </div>
                  )}
                </div>
                <div className={`text-2xl font-bold ml-4 ${textColor}`}>
                  {v > 0 ? v : ''}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Кнопка отправки */}
      <button
        onClick={handleSubmit}
        disabled={submitting || usedVotes === 0}
        className={`w-full py-4 rounded-xl font-medium text-lg transition ${
          usedVotes > 0
            ? 'bg-[#00B4A6] text-white hover:bg-[#008B7F]'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        {submitting ? 'Отправка...' : 'Проголосовать'}
      </button>
    </div>
  );
}
