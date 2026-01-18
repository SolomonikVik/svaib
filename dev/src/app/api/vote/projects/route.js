import { createServerClient } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// POST /api/vote/projects - добавить проект
export async function POST(request) {
  const supabase = createServerClient();
  const body = await request.json();

  if (!body.session_id || !body.name) {
    return NextResponse.json({ error: 'session_id, name required' }, { status: 400 });
  }

  // Получаем максимальный order_index
  const { data: existing } = await supabase
    .from('vote_projects')
    .select('order_index')
    .eq('session_id', body.session_id)
    .order('order_index', { ascending: false })
    .limit(1);

  const nextIndex = existing?.length ? existing[0].order_index + 1 : 0;

  const { data, error } = await supabase
    .from('vote_projects')
    .insert({
      session_id: body.session_id,
      name: body.name,
      description: body.description || null,
      order_index: nextIndex,
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ project: data });
}

// PATCH /api/vote/projects - обновить проект
export async function PATCH(request) {
  const supabase = createServerClient();
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'Project ID required' }, { status: 400 });
  }

  const updates = {};
  if (body.name !== undefined) updates.name = body.name;
  if (body.description !== undefined) updates.description = body.description;
  if (body.order_index !== undefined) updates.order_index = body.order_index;

  const { data, error } = await supabase
    .from('vote_projects')
    .update(updates)
    .eq('id', body.id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ project: data });
}

// DELETE /api/vote/projects - удалить проект
export async function DELETE(request) {
  const supabase = createServerClient();
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'Project ID required' }, { status: 400 });
  }

  const { error } = await supabase
    .from('vote_projects')
    .delete()
    .eq('id', id);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
