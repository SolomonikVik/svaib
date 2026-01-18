import { createServerClient } from '@/lib/supabase';
import { getWeightByPosition } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// POST /api/vote/participants - добавить участника
export async function POST(request) {
  const supabase = createServerClient();
  const body = await request.json();

  if (!body.session_id || !body.name || !body.position) {
    return NextResponse.json({ error: 'session_id, name, position required' }, { status: 400 });
  }

  const weight = getWeightByPosition(body.position);

  const { data, error } = await supabase
    .from('vote_participants')
    .insert({
      session_id: body.session_id,
      name: body.name,
      position: body.position,
      weight: weight,
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ participant: data });
}

// PATCH /api/vote/participants - обновить участника
export async function PATCH(request) {
  const supabase = createServerClient();
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'Participant ID required' }, { status: 400 });
  }

  const updates = {};
  if (body.name) updates.name = body.name;
  if (body.position) {
    updates.position = body.position;
    updates.weight = getWeightByPosition(body.position);
  }

  const { data, error } = await supabase
    .from('vote_participants')
    .update(updates)
    .eq('id', body.id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ participant: data });
}

// DELETE /api/vote/participants - удалить участника
export async function DELETE(request) {
  const supabase = createServerClient();
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'Participant ID required' }, { status: 400 });
  }

  const { error } = await supabase
    .from('vote_participants')
    .delete()
    .eq('id', id);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
