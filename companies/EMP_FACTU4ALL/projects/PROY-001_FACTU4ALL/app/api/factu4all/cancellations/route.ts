import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { checkReceivedInvoiceStatus, listPendingCancellations, respondCancellation } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const result = await listPendingCancellations(user.company_id);
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
  const action = String(body.action || "check");
  if (action === "accept" || action === "reject") {
    const uuid = String(body.uuid || "");
    if (!uuid) return NextResponse.json({ ok: false, error: "uuid requerido" }, { status: 400 });
    const result = await respondCancellation(user.company_id, uuid, action);
    return NextResponse.json(result, { status: result.ok ? 200 : 502 });
  }
  const result = await checkReceivedInvoiceStatus(user.company_id, body.uuid ? String(body.uuid) : undefined);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
