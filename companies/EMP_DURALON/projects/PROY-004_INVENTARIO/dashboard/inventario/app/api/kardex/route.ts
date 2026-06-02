import { NextResponse } from 'next/server';
import { getSupabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

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
    return NextResponse.json({ ok: true, data: data || [] });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando kardex' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const quantity = Number(body.quantity || 0);
    const isSale = body.source_type === 'remision';
    const productName = body.product_name_snapshot || null;
    const partyName = body.party_name_snapshot || null;
    const unitCost = Number(body.unit_cost || 0);
    const unitPrice = Number(body.unit_price || 0);
    const totalCost = isSale ? 0 : Number(body.total_cost || unitCost * quantity);
    const totalSale = isSale ? Number(body.total_sale || unitPrice * quantity) : 0;
    const paid = Number(body.paid_amount || 0);
    const baseAmount = isSale ? totalSale : totalCost;
    const row = {
      folio: body.folio,
      movement_type: isSale ? 'salida' : 'entrada',
      source_type: body.source_type,
      source_folio: body.source_folio || body.folio,
      external_folio: body.external_folio || null,
      purchase_folio: isSale ? null : body.source_folio || body.folio,
      remission_folio: isSale ? body.source_folio || body.folio : null,
      product_id: body.product_id,
      product_name_snapshot: productName,
      customer_id: isSale ? body.party_id : null,
      customer_name_snapshot: isSale ? partyName : null,
      supplier_id: isSale ? null : body.party_id,
      supplier_name_snapshot: isSale ? null : partyName,
      movement_date: body.movement_date,
      quantity_in: isSale ? 0 : quantity,
      quantity_out: isSale ? quantity : 0,
      unit_cost: isSale ? null : unitCost,
      unit_price: isSale ? unitPrice : null,
      total_cost: totalCost,
      total_sale: totalSale,
      paid_amount: paid,
      balance_amount: Math.max(baseAmount - paid, 0),
      payment_status: body.payment_status || (paid >= baseAmount ? 'pagado' : paid > 0 ? 'parcial' : 'pendiente'),
      notes: body.notes || null,
    };
    const { data, error } = await getSupabase().from('erp_kardex').insert(row).select().single();
    if (error) throw error;
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando movimiento' }, { status: 500 });
  }
}
