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
      .limit(100);
    if (error) throw error;
    const numbers = (data || [])
      .map((row) => {
        const match = String(row.folio || '').match(new RegExp(`^${prefix}-(\\d+)$`));
        return match ? Number(match[1]) : 0;
      })
      .filter((value) => Number.isFinite(value));
    const next = Math.max(0, ...numbers) + 1;
    return NextResponse.json({ ok: true, folio: `${prefix}-${String(next).padStart(5, '0')}` });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error generando folio' }, { status: 500 });
  }
}
