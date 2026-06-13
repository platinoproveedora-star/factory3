import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET(req: Request) {
  try {
    const params = new URL(req.url).searchParams;
    const result = await runFactorySkill<{ pedidos: any[] }>('vertical_erp_ventas/erp_ventas_pedido_list', {
      limit: params.get('limit') || '300',
      date_from: params.get('date_from') || undefined,
      date_to: params.get('date_to') || undefined,
      customer_id: params.get('customer_id') || undefined,
      status: params.get('status') || undefined,
      city: params.get('city') || undefined,
      city_quadrant: params.get('city_quadrant') || undefined,
      include_items: true,
    });
    return NextResponse.json({ ok: true, data: result.pedidos || [] }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando pedidos' }, { status: 500, headers: noStore });
  }
}
