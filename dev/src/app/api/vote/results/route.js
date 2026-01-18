import { createServerClient } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// GET /api/vote/results - получить результаты
export async function GET(request) {
  const supabase = createServerClient();
  const { searchParams } = new URL(request.url);
  const sessionId = searchParams.get('session_id');

  if (!sessionId) {
    return NextResponse.json({ error: 'session_id required' }, { status: 400 });
  }

  // 1. Получаем сессию
  const { data: session, error: sError } = await supabase
    .from('vote_sessions')
    .select('*')
    .eq('id', sessionId)
    .single();

  if (sError || !session) {
    return NextResponse.json({ error: 'Session not found' }, { status: 404 });
  }

  // 2. Получаем участников и прогресс
  const { data: participants } = await supabase
    .from('vote_participants')
    .select('*')
    .eq('session_id', sessionId)
    .order('created_at');

  const progress = {
    voted: participants.filter(p => p.has_voted).length,
    total: participants.length,
  };

  // 3. Если голосование не завершено — не показываем результаты
  if (session.status !== 'completed') {
    return NextResponse.json({
      status: session.status,
      progress,
      participants: participants.map(p => ({
        id: p.id,
        name: p.name,
        position: p.position,
        weight: p.weight,
        has_voted: p.has_voted,
      })),
      matrix: null,
    });
  }

  // 4. Получаем проекты
  const { data: projects } = await supabase
    .from('vote_projects')
    .select('*')
    .eq('session_id', sessionId)
    .order('order_index');

  // 5. Получаем все бюллетени (service_role имеет доступ)
  const participantIds = participants.map(p => p.id);
  const { data: ballots } = await supabase
    .from('vote_ballots')
    .select('*')
    .in('participant_id', participantIds);

  // 6. Строим матрицу
  const cells = {};
  const projectScores = {};

  for (const project of projects) {
    cells[project.id] = {};
    projectScores[project.id] = 0;

    for (const participant of participants) {
      const ballot = ballots.find(
        b => b.participant_id === participant.id && b.project_id === project.id
      );
      const votesGiven = ballot ? ballot.votes_given : 0;
      cells[project.id][participant.id] = votesGiven;

      // Взвешенный балл
      projectScores[project.id] += votesGiven * participant.weight;
    }
  }

  // 7. Сортируем проекты по баллам
  const sortedProjects = projects
    .map(p => ({
      id: p.id,
      name: p.name,
      description: p.description,
      totalScore: projectScores[p.id],
    }))
    .sort((a, b) => b.totalScore - a.totalScore);

  return NextResponse.json({
    status: session.status,
    progress,
    participants: participants.map(p => ({
      id: p.id,
      name: p.name,
      position: p.position,
      weight: p.weight,
    })),
    projects: sortedProjects,
    cells,
  });
}
