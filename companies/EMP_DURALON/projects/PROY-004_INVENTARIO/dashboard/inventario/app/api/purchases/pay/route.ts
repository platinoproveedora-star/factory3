import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

const noStore = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

export async function POST(req: Request) {
  try {
    const body = await req.json();
    if (!body.source_folio) {
      return NextResponse.json({ ok: false, error: 'source_folio requerido' }, { status: 400, headers: noStore });
    }
    const result = await runFactorySkill<{ source_folio: string; paid_amount: number; balance_amount: number; payment_status: string }>(
      'vertical_erp_compras/erp_compras_purchase_payment_apply',
      { ...body, dry_run: false }
    );
    return NextResponse.json({ ok: true, data: result }, { headers: noStore });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error aplicando pago' }, { status: 500, headers: noStore });
  }
}
