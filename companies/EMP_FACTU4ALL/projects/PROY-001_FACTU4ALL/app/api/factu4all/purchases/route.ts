import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { ingestPurchaseInvoice, ingestPurchaseInvoicesBatch, listPurchaseInvoices } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const result = await listPurchaseInvoices(user.company_id);
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
  if (Array.isArray(body.xmls)) {
    const xmls = body.xmls.map((x: unknown) => String(x || "")).filter(Boolean);
    if (!xmls.length) return NextResponse.json({ ok: false, error: "xmls requerido" }, { status: 400 });
    const result = await ingestPurchaseInvoicesBatch(user.company_id, xmls);
    return NextResponse.json(result, { status: result.ok ? 200 : 502 });
  }
  const xml = String(body.xml || "");
  if (!xml) return NextResponse.json({ ok: false, error: "xml requerido" }, { status: 400 });
  const result = await ingestPurchaseInvoice(user.company_id, xml, Boolean(body.preview));
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
