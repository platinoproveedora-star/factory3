import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function POST(req: Request) {
  try {
    const body = await req.json();
    if (!body.id && !body.folio) {
      return NextResponse.json({ ok: false, error: 'id o folio requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ remision: any; reversals: any[] }>('vertical_erp_ventas/erp_ventas_remision_cancel', body);
    return NextResponse.json({ ok: true, data: result }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cancelando remision' }, { status: 500, headers: noStore });
  }
}
