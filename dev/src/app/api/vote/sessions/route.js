import { createServerClient } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// GET /api/vote/sessions - получить текущую сессию (или создать новую)
export async function GET() {
  const supabase = createServerClient();

  // Получаем последнюю сессию (одна активная)
  const { data: session, error } = await supabase
    .from('vote_sessions')
    .select('*, vote_participants(*), vote_projects(*)')
    .order('created_at', { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== 'PGRST116') {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Считаем прогресс голосования
  let progress = { voted: 0, total: 0 };
  if (session?.vote_participants) {
    progress.total = session.vote_participants.length;
    progress.voted = session.vote_participants.filter(p => p.has_voted).length;
  }

  return NextResponse.json({ session, progress });
}

// POST /api/vote/sessions - создать новую сессию
export async function POST(request) {
  const supabase = createServerClient();
  const body = await request.json();

  const { data, error } = await supabase
    .from('vote_sessions')
    .insert({ name: body.name || 'Новая сессия' })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ session: data });
}

// PATCH /api/vote/sessions - обновить статус сессии
export async function PATCH(request) {
  const supabase = createServerClient();
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'Session ID required' }, { status: 400 });
  }

  const updates = {};
  if (body.status) updates.status = body.status;
  if (body.name) updates.name = body.name;
  if (body.status === 'completed') updates.completed_at = new Date().toISOString();

  const { data, error } = await supabase
    .from('vote_sessions')
    .update(updates)
    .eq('id', body.id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ session: data });
}

// DELETE /api/vote/sessions - сбросить голоса (новый раунд)
export async function DELETE(request) {
  const supabase = createServerClient();
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'Session ID required' }, { status: 400 });
  }

  // Сначала получаем ID участников сессии
  const { data: participants } = await supabase
    .from('vote_participants')
    .select('id')
    .eq('session_id', id);

  const participantIds = participants?.map(p => p.id) || [];

  // Удаляем все бюллетени этих участников
  if (participantIds.length > 0) {
    await supabase
      .from('vote_ballots')
      .delete()
      .in('participant_id', participantIds);
  }

  // Сбрасываем has_voted у всех участников
  await supabase
    .from('vote_participants')
    .update({ has_voted: false })
    .eq('session_id', id);

  // Возвращаем статус в draft
  const { data, error } = await supabase
    .from('vote_sessions')
    .update({ status: 'draft', completed_at: null })
    .eq('id', id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ session: data, message: 'Votes reset' });
}
