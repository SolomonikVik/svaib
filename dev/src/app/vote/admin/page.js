'use client';

import { useState, useEffect } from 'react';
import { POSITIONS } from '@/lib/supabase';
import { Rocket, Square, RotateCcw, BarChart3, Check } from 'lucide-react';

export default function AdminPage() {
  const [session, setSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [projects, setProjects] = useState([]);
  const [progress, setProgress] = useState({ voted: 0, total: 0 });
  const [loading, setLoading] = useState(true);

  // Формы
  const [newSessionName, setNewSessionName] = useState('');
  const [newParticipant, setNewParticipant] = useState({ name: '', position: 'Специалист' });
  const [newProject, setNewProject] = useState({ name: '', description: '' });

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
      setProgress(data.progress);
    }
    setLoading(false);
  }

  async function createSession() {
    if (!newSessionName.trim()) return;

    const res = await fetch('/api/vote/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newSessionName }),
    });

    const data = await res.json();
    if (data.session) {
      setSession(data.session);
      setParticipants([]);
      setProjects([]);
      setNewSessionName('');
    }
  }

  async function addParticipant() {
    if (!newParticipant.name.trim() || !session) return;

    const res = await fetch('/api/vote/participants', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session.id,
        name: newParticipant.name,
        position: newParticipant.position,
      }),
    });

    const data = await res.json();
    if (data.participant) {
      setParticipants([...participants, data.participant]);
      setNewParticipant({ name: '', position: 'Специалист' });
    }
  }

  async function removeParticipant(id) {
    await fetch(`/api/vote/participants?id=${id}`, { method: 'DELETE' });
    setParticipants(participants.filter(p => p.id !== id));
  }

  async function addProject() {
    if (!newProject.name.trim() || !session) return;

    const res = await fetch('/api/vote/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session.id,
        name: newProject.name,
        description: newProject.description,
      }),
    });

    const data = await res.json();
    if (data.project) {
      setProjects([...projects, data.project]);
      setNewProject({ name: '', description: '' });
    }
  }

  async function removeProject(id) {
    await fetch(`/api/vote/projects?id=${id}`, { method: 'DELETE' });
    setProjects(projects.filter(p => p.id !== id));
  }

  async function updateStatus(status) {
    const res = await fetch('/api/vote/sessions', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: session.id, status }),
    });

    const data = await res.json();
    if (data.session) {
      setSession(data.session);
    }
  }

  async function resetVotes() {
    if (!confirm('Сбросить все голоса? Это действие нельзя отменить.')) return;

    const res = await fetch(`/api/vote/sessions?id=${session.id}`, { method: 'DELETE' });
    const data = await res.json();

    if (data.session) {
      setSession(data.session);
      loadSession();
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  }

  // Нет сессии — создать новую
  if (!session) {
    return (
      <div className="max-w-md mx-auto">
        <h1 className="font-heading text-2xl font-bold text-gray-800 mb-6">Создать сессию</h1>
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Название (например: Стратсессия Q1 2026)"
            value={newSessionName}
            onChange={e => setNewSessionName(e.target.value)}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:border-[#00B4A6]"
          />
          <button
            onClick={createSession}
            disabled={!newSessionName.trim()}
            className="w-full bg-[#00B4A6] text-white py-3 rounded-xl font-medium hover:bg-[#008B7F] transition disabled:bg-gray-200 disabled:text-gray-400"
          >
            Создать сессию
          </button>
        </div>
      </div>
    );
  }

  const statusColors = {
    draft: 'bg-gray-200 text-gray-600',
    voting: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-[#E0F7F5] text-[#00B4A6]',
  };

  const statusLabels = {
    draft: 'Подготовка',
    voting: 'Идёт голосование',
    completed: 'Завершено',
  };

  return (
    <div className="space-y-8">
      {/* Заголовок и статус */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-gray-800">{session.name}</h1>
          <span className={`inline-block mt-2 px-3 py-1 rounded-full text-sm font-medium ${statusColors[session.status]}`}>
            {statusLabels[session.status]}
          </span>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500">Проголосовало</div>
          <div className="text-2xl font-bold text-gray-800">{progress.voted} / {progress.total}</div>
        </div>
      </div>

      {/* Участники */}
      <section className="bg-white rounded-xl p-6 border border-gray-200">
        <h2 className="font-heading text-lg font-semibold text-gray-800 mb-4">Участники ({participants.length})</h2>

        <div className="space-y-2 mb-4">
          {participants.map(p => (
            <div key={p.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <span className="font-medium text-gray-800">{p.name}</span>
                <span className="ml-2 text-sm text-gray-500">
                  {POSITIONS.find(pos => pos.value === p.position)?.label} (вес: {p.weight})
                </span>
                {p.has_voted && <Check className="inline ml-2 w-4 h-4 text-[#00B4A6]" />}
              </div>
              {session.status === 'draft' && (
                <button
                  onClick={() => removeParticipant(p.id)}
                  className="text-red-400 hover:text-red-600 text-sm"
                >
                  Удалить
                </button>
              )}
            </div>
          ))}
        </div>

        {session.status === 'draft' && (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Имя"
              value={newParticipant.name}
              onChange={e => setNewParticipant({ ...newParticipant, name: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-[#00B4A6]"
            />
            <select
              value={newParticipant.position}
              onChange={e => setNewParticipant({ ...newParticipant, position: e.target.value })}
              className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-[#00B4A6]"
            >
              {POSITIONS.map(pos => (
                <option key={pos.value} value={pos.value}>{pos.label}</option>
              ))}
            </select>
            <button
              onClick={addParticipant}
              disabled={!newParticipant.name.trim()}
              className="px-4 py-2 bg-[#00B4A6] text-white rounded-lg hover:bg-[#008B7F] disabled:bg-gray-200 disabled:text-gray-400"
            >
              +
            </button>
          </div>
        )}
      </section>

      {/* Проекты */}
      <section className="bg-white rounded-xl p-6 border border-gray-200">
        <h2 className="font-heading text-lg font-semibold text-gray-800 mb-4">Проекты ({projects.length})</h2>

        <div className="space-y-2 mb-4">
          {projects.map((p, i) => (
            <div key={p.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <span className="text-gray-400 mr-2">{i + 1}.</span>
                <span className="font-medium text-gray-800">{p.name}</span>
                {p.description && <span className="ml-2 text-sm text-gray-500">— {p.description}</span>}
              </div>
              {session.status === 'draft' && (
                <button
                  onClick={() => removeProject(p.id)}
                  className="text-red-400 hover:text-red-600 text-sm"
                >
                  Удалить
                </button>
              )}
            </div>
          ))}
        </div>

        {session.status === 'draft' && (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Название проекта"
              value={newProject.name}
              onChange={e => setNewProject({ ...newProject, name: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-[#00B4A6]"
            />
            <input
              type="text"
              placeholder="Комментарий (опционально)"
              value={newProject.description}
              onChange={e => setNewProject({ ...newProject, description: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-[#00B4A6]"
            />
            <button
              onClick={addProject}
              disabled={!newProject.name.trim()}
              className="px-4 py-2 bg-[#00B4A6] text-white rounded-lg hover:bg-[#008B7F] disabled:bg-gray-200 disabled:text-gray-400"
            >
              +
            </button>
          </div>
        )}
      </section>

      {/* Управление */}
      <section className="bg-white rounded-xl p-6 border border-gray-200">
        <h2 className="font-heading text-lg font-semibold text-gray-800 mb-4">Управление</h2>

        <div className="flex flex-wrap gap-3">
          {session.status === 'draft' && participants.length >= 2 && projects.length >= 2 && (
            <button
              onClick={() => updateStatus('voting')}
              className="px-6 py-3 bg-[#00B4A6] text-white rounded-xl font-medium hover:bg-[#008B7F] transition flex items-center gap-2"
            >
              <Rocket className="w-5 h-5" /> Запустить голосование
            </button>
          )}

          {session.status === 'voting' && (
            <button
              onClick={() => updateStatus('completed')}
              className="px-6 py-3 bg-yellow-500 text-white rounded-xl font-medium hover:bg-yellow-600 transition flex items-center gap-2"
            >
              <Square className="w-5 h-5" /> Завершить досрочно
            </button>
          )}

          {(session.status === 'voting' || session.status === 'completed') && (
            <button
              onClick={resetVotes}
              className="px-6 py-3 bg-red-100 text-red-600 rounded-xl font-medium hover:bg-red-200 transition flex items-center gap-2"
            >
              <RotateCcw className="w-5 h-5" /> Сбросить всё
            </button>
          )}

          {session.status === 'completed' && (
            <a
              href="/vote/results"
              className="px-6 py-3 bg-[#E0F7F5] text-[#00B4A6] rounded-xl font-medium hover:bg-[#00B4A6] hover:text-white transition flex items-center gap-2"
            >
              <BarChart3 className="w-5 h-5" /> Смотреть результаты
            </a>
          )}
        </div>

        {session.status === 'draft' && (participants.length < 2 || projects.length < 2) && (
          <p className="mt-4 text-sm text-gray-500">
            Для запуска нужно минимум 2 участника и 2 проекта
          </p>
        )}
      </section>
    </div>
  );
}
