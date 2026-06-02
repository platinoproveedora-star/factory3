import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

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
    const row = {
      folio: body.folio,
      product_key: body.product_key || null,
      product_name: body.product_name,
      sku: body.sku || null,
      category: body.category || null,
      unit: body.unit || 'pieza',
      min_stock: Number(body.min_stock || 0),
      active: body.active !== false,
      is_key_product: Boolean(body.is_key_product),
    };
    const { data, error } = await getSupabase().from('erp_products').insert(row).select().single();
    if (error) throw error;
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando producto' }, { status: 500 });
  }
}
