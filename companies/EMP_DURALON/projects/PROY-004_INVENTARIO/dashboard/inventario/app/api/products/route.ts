import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const { data, error } = await getSupabase()
      .from('erp_products')
      .select('*')
      .order('product_name', { ascending: true });
    if (error) throw error;
    return NextResponse.json({ ok: true, data: data || [] });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando productos' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const result = await runFactorySkill<{ product: any }>('vertical_erp_inventory/erp_inventory_product_save', body);
    return NextResponse.json({ ok: true, data: result.product });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando producto' }, { status: 500 });
  }
}
