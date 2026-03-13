import { NextResponse } from 'next/server';
import { isInternalVoteEnabled } from '@/lib/site';

export function ensureInternalVoteEnabled() {
  if (!isInternalVoteEnabled()) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  return null;
}

