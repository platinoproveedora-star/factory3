import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const supabase = getSupabase();
    const [productsRes, partiesRes, kardexRes] = await Promise.all([
      supabase.from('erp_products').select('*').order('product_name', { ascending: true }),
      supabase.from('erp_parties').select('*').order('party_name', { ascending: true }),
      supabase.from('erp_kardex').select('*').order('movement_date', { ascending: false }).limit(500),
    ]);
    if (productsRes.error) throw productsRes.error;
    if (partiesRes.error) throw partiesRes.error;
    if (kardexRes.error) throw kardexRes.error;

    const products = productsRes.data || [];
    const parties = partiesRes.data || [];
    const movements = kardexRes.data || [];
    const productNames = new Map(products.map((p: any) => [p.id, p.product_name]));
    const stockMap = new Map<string, any>();
    for (const movement of movements as any[]) {
      const row = stockMap.get(movement.product_id) || {
        product_id: movement.product_id,
        product_name: productNames.get(movement.product_id) || movement.product_name_snapshot || 'Producto',
        quantity: 0,
        total_in: 0,
        total_out: 0,
      };
      row.total_in += Number(movement.quantity_in || 0);
      row.total_out += Number(movement.quantity_out || 0);
      row.quantity = row.total_in - row.total_out;
      stockMap.set(movement.product_id, row);
    }
    const sales = movements.filter((m: any) => m.source_type === 'remision');
    const purchases = movements.filter((m: any) => m.source_type === 'compra');
    return NextResponse.json({
      ok: true,
      data: {
        products,
        customers: parties.filter((p: any) => ['customer', 'both'].includes(p.party_type)),
        suppliers: parties.filter((p: any) => ['supplier', 'both'].includes(p.party_type)),
        purchases,
        sales,
        stock: Array.from(stockMap.values()).sort((a, b) => b.quantity - a.quantity),
        receivables_total: sales.reduce((sum: number, row: any) => sum + Number(row.balance_amount || 0), 0),
        payables_total: purchases.reduce((sum: number, row: any) => sum + Number(row.balance_amount || 0), 0),
      },
    });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando resumen' }, { status: 500 });
  }
}
