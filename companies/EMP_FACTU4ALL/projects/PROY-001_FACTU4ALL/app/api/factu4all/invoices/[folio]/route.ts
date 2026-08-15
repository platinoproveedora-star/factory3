import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { cancelInvoice, downloadInvoiceFile, invoiceStatus } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest, { params }: { params: Promise<{ folio: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const { folio } = await params;
  const body = await req.json().catch(() => ({}));
  const action = String(body.action || "");

  let result;
  if (action === "cancel") {
    result = await cancelInvoice(user.company_id, folio, body.motivo);
  } else if (action === "status") {
    result = await invoiceStatus(user.company_id, folio);
  } else if (action === "download") {
    result = await downloadInvoiceFile(user.company_id, folio, body.file_type === "pdf" ? "pdf" : "xml");
  } else {
    return NextResponse.json({ ok: false, error: "action debe ser cancel|status|download" }, { status: 400 });
  }
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
