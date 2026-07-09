import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireFleetCompanyAccess } from "@/lib/access";
import { expenseCategoryManage } from "@/lib/fleet4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const params = new URL(req.url).searchParams;
  const empresaId = String(params.get("empresa_id") || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await expenseCategoryManage({ action: "list", empresa_id: empresaId });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await expenseCategoryManage({ ...body, empresa_id: empresaId, dry_run: false });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
