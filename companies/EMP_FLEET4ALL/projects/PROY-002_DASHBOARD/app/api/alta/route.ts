import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireFleetCompanyAccess } from "@/lib/access";
import { driverManage, unitManage } from "@/lib/fleet4all";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }

  const action = String(body.action || "").trim().toLowerCase();
  const result =
    action === "driver" ? await driverManage({ ...body, dry_run: false }) :
    action === "unit" ? await unitManage({ ...body, dry_run: false }) :
    { ok: false, error: "action_invalida" };
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
