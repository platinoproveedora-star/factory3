import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { loadLogisticsData } from "@/lib/logistics";
import { isPlatformAdmin, listGrants, logisticsGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });
  const grants = logisticsGrants(await listGrants(user.sub));
  if (!grants.length) return NextResponse.json({ ok: false, error: "sin acceso" }, { status: 403 });
  const requested = req.nextUrl.searchParams.get("company_id") || user.company_id;
  const allowed = isPlatformAdmin(grants) || grants.some((grant) => grant.company_id === requested);
  if (!allowed) return NextResponse.json({ ok: false, error: "sin acceso a empresa" }, { status: 403 });
  const result = await loadLogisticsData(user, grants, requested);
  return NextResponse.json(result.ok ? { ok: true, data: result.data } : { ok: false, error: result.error }, { status: result.ok ? 200 : 500 });
}
