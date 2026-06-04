import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function GET() {
  try {
    const result = await runFactorySkill<{ lots: any[]; summary: any }>('vertical_erp_inventory/erp_inventory_lot_stock_report', {});
    return NextResponse.json({ ok: true, data: result.lots || [], summary: result.summary || {} }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error cargando lotes' }, { status: 500, headers: noStore });
  }
}
