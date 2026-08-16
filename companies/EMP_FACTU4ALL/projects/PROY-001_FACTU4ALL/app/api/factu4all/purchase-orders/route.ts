import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { createPurchaseOrder, listPendingPurchaseOrders } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const result = await listPendingPurchaseOrders(user.company_id);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const body = await req.json().catch(() => ({}));
  const result = await createPurchaseOrder(user.company_id, body);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
