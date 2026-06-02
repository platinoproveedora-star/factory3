import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET(req: Request) {
  try {
    const type = new URL(req.url).searchParams.get('type');
    const result = await runFactorySkill<any>('vertical_erp_inventory/erp_inventory_dashboard_data', { action: 'dashboard' });
    const data = type === 'supplier' ? result.suppliers : type === 'customer' ? result.customers : [...(result.customers || []), ...(result.suppliers || [])];
    return NextResponse.json({ ok: true, data: data || [] }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando terceros' }, { status: 500, headers: noStore });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const result = await runFactorySkill<{ party: any }>('vertical_erp_inventory/erp_inventory_party_save', body);
    return NextResponse.json({ ok: true, data: result.party }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error guardando tercero' }, { status: 500, headers: noStore });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    if (!body.id) {
      return NextResponse.json({ ok: false, error: 'id es requerido' }, { status: 400, headers: noStore });
    }
    if (!String(body.party_name || '').trim()) {
      return NextResponse.json({ ok: false, error: 'nombre es requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ party: any }>('vertical_erp_inventory/erp_inventory_party_save', body);
    return NextResponse.json({ ok: true, data: result.party }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error actualizando tercero' }, { status: 500, headers: noStore });
  }
}

export async function DELETE(req: Request) {
  try {
    const body = await req.json();
    if (!body.id) {
      return NextResponse.json({ ok: false, error: 'id es requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ party: any }>('vertical_erp_inventory/erp_inventory_party_delete', body);
    return NextResponse.json({ ok: true, data: result.party }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error borrando tercero' }, { status: 500, headers: noStore });
  }
}
