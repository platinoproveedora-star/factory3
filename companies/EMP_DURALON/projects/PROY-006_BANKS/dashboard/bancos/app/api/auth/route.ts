import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

function expectedKey() {
  return String(process.env.DASHBOARD_KEY || '').trim();
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const configured = expectedKey();
  const received = String(body.key || '').trim();

  if (!configured) {
    return NextResponse.json({ ok: false, error: 'DASHBOARD_KEY no configurada' }, { status: 500 });
  }

  if (!received || received !== configured) {
    return NextResponse.json({ ok: false, error: 'Clave invalida' }, { status: 401 });
  }

  return NextResponse.json({ ok: true, data: { authenticated: true } });
}
