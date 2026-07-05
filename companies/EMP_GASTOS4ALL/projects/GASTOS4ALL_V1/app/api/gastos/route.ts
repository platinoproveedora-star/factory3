import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { calcStats, createGasto, deleteGasto, getGastos, updateGasto } from "@/lib/db";
import { listGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function requireSession(companyId?: string | null) {
  const session = await getSession();
  if (!session) return { ok: false as const, status: 401, error: "sesion requerida" };
  const grants = await listGrants(session.sub);
  const moduleGrants = grants.filter((grant) => grant.modulo_code === "gastos4all");
  const grant = companyId
    ? moduleGrants.find((item) => item.company_id === companyId)
    : moduleGrants[0];
  if (!grant) return { ok: false as const, status: 403, error: "sin acceso a gastos4all" };
  return { ok: true as const, session, empresaId: grant.company_id };
}

export async function GET(req: NextRequest) {
  const access = await requireSession(req.nextUrl.searchParams.get("company_id"));
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  try {
    const gastos = await getGastos(access.empresaId, 2000);
    return NextResponse.json({ ok: true, gastos, stats: calcStats(gastos) });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "no se pudieron cargar gastos" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const access = await requireSession(String(body.company_id || ""));
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const empresaId = access.empresaId;
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
    return NextResponse.json({ ok: false, error: "action invalida" }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "operacion fallida" }, { status: 500 });
  }
}
