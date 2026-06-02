import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET(req: Request) {
  try {
    const sourceType = new URL(req.url).searchParams.get('source_type');
    let query = getSupabase()
      .from('erp_kardex')
      .select('*')
      .order('movement_date', { ascending: false })
      .order('created_at', { ascending: false })
      .limit(500);
    if (sourceType) query = query.eq('source_type', sourceType);
    const { data, error } = await query;
    if (error) throw error;
    return NextResponse.json({ ok: true, data: data || [] }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando kardex' }, { status: 500, headers: noStore });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const result = await runFactorySkill<{ movement: any }>('vertical_erp_inventory/erp_inventory_kardex_save', body);
    return NextResponse.json({ ok: true, data: result.movement }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando movimiento' }, { status: 500, headers: noStore });
  }
}
