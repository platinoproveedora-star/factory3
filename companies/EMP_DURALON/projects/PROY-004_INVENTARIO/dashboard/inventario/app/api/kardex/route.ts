import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET(req: Request) {
  try {
    const params = new URL(req.url).searchParams;
    const result = await runFactorySkill<{ movements: any[] }>('vertical_erp_inventory/erp_inventory_kardex_list', {
      source_type: params.get('source_type') || undefined,
      product_id: params.get('product_id') || undefined,
      start_date: params.get('start_date') || undefined,
      end_date: params.get('end_date') || undefined,
      limit: params.get('limit') || undefined,
    });
    return NextResponse.json({ ok: true, data: result.movements || [] }, { headers: noStore });
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
