import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { createGasto, deleteGasto, listBankAccounts, listCategories, listGastos, summarize, updateGasto } from "@/lib/gastos";
import { listGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function requireGastosAccess() {
  const user = await getSession();
  if (!user) return { ok: false as const, status: 401, error: "sesion requerida" };
  const gastosCompanyId = process.env.GASTOS_COMPANY_ID;
  if (!gastosCompanyId) return { ok: false as const, status: 500, error: "GASTOS_COMPANY_ID requerido" };
  const grants = await listGrants(user.sub);
  const grant = grants.find((item) => item.company_id === gastosCompanyId && item.modulo_code === "gastos");
  if (!grant) return { ok: false as const, status: 403, error: "sin acceso a gastos" };
  return { ok: true as const, user };
}

export async function GET() {
  const access = await requireGastosAccess();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  try {
    const [gastos, categories, bankAccounts] = await Promise.all([listGastos(), listCategories(), listBankAccounts()]);
    return NextResponse.json({ ok: true, gastos, stats: summarize(gastos), categories: categories.map((item) => item.nombre), bankAccounts });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "no se pudieron cargar gastos" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const access = await requireGastosAccess();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const body = await req.json().catch(() => ({}));
  try {
    if (body.action === "create") {
      const gasto = await createGasto(body, access.user);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "update") {
      const gasto = await updateGasto(body, access.user);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "delete") {
      const result = await deleteGasto(String(body.folio || ""), access.user);
      return NextResponse.json({ ok: true, ...result });
    }
    return NextResponse.json({ ok: false, error: "action invalida" }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "operacion fallida" }, { status: 500 });
  }
}
