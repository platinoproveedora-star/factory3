import { NextResponse } from 'next/server';
import { runFactorySkill } from '../../../../../lib/factory';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

export async function GET(req: Request) {
  try {
    const params = new URL(req.url).searchParams;
    const result = await runFactorySkill<{ html: string }>('vertical_erp_compras/erp_compras_purchase_pdf', {
      folio: params.get('folio') || undefined,
    });
    return new NextResponse(result.html, {
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
      },
    });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error generando PDF' }, { status: 500 });
  }
}
