import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET() {
  try {
    const result = await runFactorySkill<{ stock: any[] }>('vertical_erp_inventory/erp_inventory_current_stock_report', {});
    return NextResponse.json({ ok: true, data: result.stock || [] }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando productos' }, { status: 500, headers: noStore });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    if (!body.id && !body.product_id) {
      return NextResponse.json({ ok: false, error: 'id es requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ product: any }>('vertical_erp_inventory/erp_inventory_product_update', body);
    return NextResponse.json({ ok: true, data: result.product }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error actualizando producto' }, { status: 500, headers: noStore });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const result = await runFactorySkill<{ product: any }>('vertical_erp_inventory/erp_inventory_product_save', body);
    return NextResponse.json({ ok: true, data: result.product }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando producto' }, { status: 500, headers: noStore });
  }
}
