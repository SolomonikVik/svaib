import { createServerClient } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// POST /api/vote/cast - подать голос
export async function POST(request) {
  const supabase = createServerClient();
  const body = await request.json();

  const { participant_id, votes } = body;

  if (!participant_id || !votes || !Array.isArray(votes)) {
    return NextResponse.json({ error: 'participant_id and votes[] required' }, { status: 400 });
  }

  // 1. Проверяем участника
  const { data: participant, error: pError } = await supabase
    .from('vote_participants')
    .select('*, vote_sessions(*)')
    .eq('id', participant_id)
    .single();

  if (pError || !participant) {
    return NextResponse.json({ error: 'Participant not found' }, { status: 404 });
  }

  if (participant.has_voted) {
    return NextResponse.json({ error: 'Already voted' }, { status: 400 });
  }

  if (participant.vote_sessions.status !== 'voting') {
    return NextResponse.json({ error: 'Voting not active' }, { status: 400 });
  }

  // 2. Получаем количество проектов для валидации
  const { count: projectCount } = await supabase
    .from('vote_projects')
    .select('*', { count: 'exact', head: true })
    .eq('session_id', participant.session_id);

  const maxVotes = Math.ceil(projectCount / 2);
  const totalVotes = votes.reduce((sum, v) => sum + v.votes_given, 0);

  if (totalVotes > maxVotes) {
    return NextResponse.json({
      error: `Too many votes: ${totalVotes} > ${maxVotes}`
    }, { status: 400 });
  }

  // 3. Валидация голосов (1 или 2)
  for (const vote of votes) {
    if (vote.votes_given !== 1 && vote.votes_given !== 2) {
      return NextResponse.json({ error: 'votes_given must be 1 or 2' }, { status: 400 });
    }
  }

  // 4. Вставляем бюллетени
  const ballots = votes.map(v => ({
    participant_id,
    project_id: v.project_id,
    votes_given: v.votes_given,
  }));

  const { error: bError } = await supabase
    .from('vote_ballots')
    .insert(ballots);

  if (bError) {
    return NextResponse.json({ error: bError.message }, { status: 500 });
  }

  // 5. Отмечаем что участник проголосовал
  await supabase
    .from('vote_participants')
    .update({ has_voted: true })
    .eq('id', participant_id);

  // 6. Проверяем, все ли проголосовали
  const { data: allParticipants } = await supabase
    .from('vote_participants')
    .select('has_voted')
    .eq('session_id', participant.session_id);

  const allVoted = allParticipants.every(p => p.has_voted);

  if (allVoted) {
    await supabase
      .from('vote_sessions')
      .update({ status: 'completed', completed_at: new Date().toISOString() })
      .eq('id', participant.session_id);
  }

  return NextResponse.json({
    success: true,
    allVoted,
    message: allVoted ? 'All participants voted!' : 'Vote recorded'
  });
}
