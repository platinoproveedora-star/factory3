import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET(req: Request) {
  try {
    const params = new URL(req.url).searchParams;
    const action = params.get('action') || 'list';
    if (action === 'detail') {
      const result = await runFactorySkill<{ remision: any; items: any[] }>('vertical_erp_ventas/erp_ventas_remision_detail', {
        id: params.get('id') || undefined,
        folio: params.get('folio') || undefined,
      });
      return NextResponse.json({ ok: true, data: result }, { headers: noStore });
    }
    if (action === 'matrix') {
      const result = await runFactorySkill<any>('vertical_erp_ventas/erp_ventas_key_product_matrix', {
        start_date: params.get('start_date') || undefined,
        end_date: params.get('end_date') || undefined,
      });
      return NextResponse.json({ ok: true, data: result }, { headers: noStore });
    }
    const limit = params.get('limit') || '300';
    const result = await runFactorySkill<{ remisiones: any[] }>('vertical_erp_ventas/erp_ventas_remision_list', {
      limit,
      start_date: params.get('start_date') || undefined,
      end_date: params.get('end_date') || undefined,
    });
    return NextResponse.json({ ok: true, data: result.remisiones || [] }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando remisiones' }, { status: 500, headers: noStore });
  }
}

export async function PUT(req: Request) {
  try {
    const body = await req.json();
    if (!body.id && !body.folio) {
      return NextResponse.json({ ok: false, error: 'id o folio requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ remision: any; items: any[] }>('vertical_erp_ventas/erp_ventas_remision_full_update', body);
    return NextResponse.json({ ok: true, data: result }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error actualizando remision completa' }, { status: 500, headers: noStore });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    if (!body.id && !body.folio) {
      return NextResponse.json({ ok: false, error: 'id o folio requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ remision: any }>('vertical_erp_ventas/erp_ventas_remision_update', body);
    return NextResponse.json({ ok: true, data: result.remision }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error actualizando remision' }, { status: 500, headers: noStore });
  }
}
