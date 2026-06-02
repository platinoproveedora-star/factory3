import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const table = searchParams.get('table') || '';
    const prefix = (searchParams.get('prefix') || '').toUpperCase();
    if (!/^[a-z][a-z0-9_]*$/.test(table) || !/^[A-Z]{3,5}$/.test(prefix)) {
      return NextResponse.json({ ok: false, error: 'Parametros invalidos' }, { status: 400 });
    }
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from(table)
      .select('folio')
      .ilike('folio', `${prefix}-%`)
      .order('folio', { ascending: false })
      .limit(1);
    if (error) throw error;
    const last = data?.[0]?.folio || `${prefix}-00000`;
    const next = Number(String(last).split('-').pop() || '0') + 1;
    return NextResponse.json({ ok: true, folio: `${prefix}-${String(next).padStart(5, '0')}` });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error generando folio' }, { status: 500 });
  }
}
