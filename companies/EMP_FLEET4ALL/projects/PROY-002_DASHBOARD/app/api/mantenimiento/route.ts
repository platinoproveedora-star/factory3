import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireFleetCompanyAccess } from "@/lib/access";
import { maintenanceSchedule, serviceCapture, partsKardex, unitRecord } from "@/lib/fleet4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const s = new URL(req.url).searchParams;
  const empresaId = s.get("empresa_id");
  const unitKey = s.get("unit_key");
  if (!empresaId || !unitKey) return NextResponse.json({ ok: false, error: "empresa_id y unit_key requeridos" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await unitRecord({ empresa_id: empresaId, unit_key: unitKey });
  return NextResponse.json(result);
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
  const action = body.action || "plan";
  const result =
    action === "service" ? await serviceCapture(body) :
    action === "kardex" ? await partsKardex(body) :
    await maintenanceSchedule(body);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
