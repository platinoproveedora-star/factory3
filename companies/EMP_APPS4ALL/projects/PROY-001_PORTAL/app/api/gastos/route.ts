import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { createGasto, deleteGasto, listBankAccounts, listCategories, listGastos, summarize, updateGasto } from "@/lib/gastos";
import { listGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function requireGastosAccess() {
  const user = await getSession();
  if (!user) return { ok: false as const, status: 401, error: "sesion requerida" };
  const grants = await listGrants(user.sub);
  const grant = grants.find((item) => item.modulo_code === "gastos");
  if (!grant) return { ok: false as const, status: 403, error: "sin acceso a gastos" };
  return { ok: true as const, user, companyId: grant.company_id };
}

export async function GET() {
  const access = await requireGastosAccess();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const companyId = access.companyId;
  try {
    const [gastos, categories, bankAccounts] = await Promise.all([
      listGastos(companyId),
      listCategories(companyId),
      listBankAccounts(companyId)
    ]);
    return NextResponse.json({ ok: true, gastos, stats: summarize(gastos), categories: categories.map((item) => item.nombre), bankAccounts });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "no se pudieron cargar gastos" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const access = await requireGastosAccess();
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const { companyId } = access;
  const body = await req.json().catch(() => ({}));
  try {
    if (body.action === "create") {
      const gasto = await createGasto(body, access.user, companyId);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "update") {
      const gasto = await updateGasto(body, access.user, companyId);
      return NextResponse.json({ ok: true, gasto });
    }
    if (body.action === "delete") {
      const result = await deleteGasto(String(body.folio || ""), access.user, companyId);
      return NextResponse.json({ ok: true, ...result });
    }
    return NextResponse.json({ ok: false, error: "action invalida" }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "operacion fallida" }, { status: 500 });
  }
}
