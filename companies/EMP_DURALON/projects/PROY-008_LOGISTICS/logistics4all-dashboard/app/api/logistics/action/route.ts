import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { callFactory } from "@/lib/factory";
import { logisticsContext } from "@/lib/logistics";
import { isPlatformAdmin, listGrants, logisticsGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";

const ACTION_SKILLS: Record<string, string> = {
  create_trip: "vertical_apps4all_logistics/logistics_trip_create",
  assign_orders: "vertical_apps4all_logistics/logistics_trip_assign_orders",
  manage_trip: "vertical_apps4all_logistics/logistics_trip_manage",
  catalog_manage: "vertical_apps4all_logistics/logistics_catalog_manage"
};

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });
  const body = await req.json().catch(() => null);
  const action = String(body?.action || "");
  const skill = ACTION_SKILLS[action];
  if (!skill) return NextResponse.json({ ok: false, error: "accion invalida" }, { status: 400 });
  const grants = logisticsGrants(await listGrants(user.sub));
  if (!grants.length) return NextResponse.json({ ok: false, error: "sin acceso" }, { status: 403 });
  const companyId = String(body?.company_id || user.company_id);
  const allowed = isPlatformAdmin(grants) || grants.some((grant) => grant.company_id === companyId);
  if (!allowed) return NextResponse.json({ ok: false, error: "sin acceso a empresa" }, { status: 403 });
  const context = {
    ...logisticsContext(user, grants, companyId),
    ...(body?.context || {}),
    dry_run: body?.dry_run ?? false
  };
  const result = await callFactory(skill, context, "run");
  return NextResponse.json(result.ok ? { ok: true, data: result.data } : { ok: false, error: result.error }, { status: result.ok ? 200 : 500 });
}
