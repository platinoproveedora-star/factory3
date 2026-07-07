import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { createCategory, listAllCategories, setCategoryActive } from "@/lib/db";
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
    const categorias = await listAllCategories(access.empresaId);
    return NextResponse.json({ ok: true, categorias });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "no se pudieron cargar categorías" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const access = await requireSession(String(body.company_id || ""));
  if (!access.ok) return NextResponse.json({ ok: false, error: access.error }, { status: access.status });
  const empresaId = access.empresaId;
  try {
    if (body.action === "create") {
      const categoria = await createCategory(empresaId, String(body.nombre || ""));
      return NextResponse.json({ ok: true, categoria });
    }
    if (body.action === "toggle") {
      const categoria = await setCategoryActive(empresaId, String(body.id || ""), Boolean(body.activo));
      return NextResponse.json({ ok: true, categoria });
    }
    return NextResponse.json({ ok: false, error: "action invalida" }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "operacion fallida" }, { status: 400 });
  }
}
