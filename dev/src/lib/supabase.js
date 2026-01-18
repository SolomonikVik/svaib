import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Browser client (RLS применяется)
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Server client (service_role для API routes)
export function createServerClient() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!serviceKey) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY is required');
  }

  return createClient(url, serviceKey);
}

// Фиксированные должности
export const POSITIONS = [
  { value: 'CEO', label: 'CEO', weight: 5 },
  { value: 'C-1', label: 'C-1 (CTO, CFO...)', weight: 3 },
  { value: 'C-2', label: 'C-2 (Directors)', weight: 2 },
  { value: 'Специалист', label: 'Специалист', weight: 1 },
];

export function getWeightByPosition(position) {
  const found = POSITIONS.find(p => p.value === position);
  return found ? found.weight : 1;
}
