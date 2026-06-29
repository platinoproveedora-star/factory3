import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { calcStats, createGasto, deleteGasto, getGastos, updateGasto } from "@/lib/db";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function requireSession() {
  const session = await getSession();
  if (!session) return { ok: false as const, status: 401, error: "sesión requerida" };
  return { ok: true as const, session };
}

export async function GET() {
  const access = await requireSession();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  try {
    const gastos = await getGastos(access.session.company_id, 2000);
    return NextResponse.json({ ok: true, gastos, stats: calcStats(gastos) });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "no se pudieron cargar gastos" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const access = await requireSession();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const empresaId = access.session.company_id;
  const body = await req.json().catch(() => ({}));
  try {
    if (body.action === "create") {
      const gasto = await createGasto(empresaId, body);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "update") {
      const gasto = await updateGasto(empresaId, body);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "delete") {
      const result = await deleteGasto(empresaId, String(body.folio || ""));
      return NextResponse.json({ ok: true, ...result });
    }
    return NextResponse.json({ ok: false, error: "action inválida" }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "operación fallida" }, { status: 500 });
  }
}
