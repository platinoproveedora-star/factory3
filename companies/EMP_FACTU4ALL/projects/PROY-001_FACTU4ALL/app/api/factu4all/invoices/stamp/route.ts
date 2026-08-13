import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { stampInvoice } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const body = await req.json().catch(() => ({}));
  const folio = String(body.folio || "");
  if (!folio) return NextResponse.json({ ok: false, error: "folio requerido" }, { status: 400 });
  const result = await stampInvoice(user.company_id, folio);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
