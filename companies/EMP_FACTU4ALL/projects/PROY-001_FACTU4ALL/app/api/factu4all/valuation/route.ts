import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { listInventoryValuation } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const environment = req.nextUrl.searchParams.get("environment") || undefined;
  const result = await listInventoryValuation(user.company_id, environment);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
