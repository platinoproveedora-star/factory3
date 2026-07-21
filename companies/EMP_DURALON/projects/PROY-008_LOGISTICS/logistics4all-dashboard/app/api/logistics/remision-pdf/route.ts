import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { callFactory } from "@/lib/factory";
import { logisticsContext } from "@/lib/logistics";
import { isPlatformAdmin, listGrants, logisticsGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });
  const grants = logisticsGrants(await listGrants(user.sub));
  if (!grants.length) return NextResponse.json({ ok: false, error: "sin acceso" }, { status: 403 });

  const params = req.nextUrl.searchParams;
  const companyId = String(params.get("company_id") || user.company_id);
  const allowed = isPlatformAdmin(grants) || grants.some((grant) => grant.company_id === companyId);
  if (!allowed) return NextResponse.json({ ok: false, error: "sin acceso a empresa" }, { status: 403 });

  const folio = String(params.get("folio") || "").trim();
  if (!folio) return NextResponse.json({ ok: false, error: "folio requerido" }, { status: 400 });

  const result = await callFactory<{ html: string }>(
    "vertical_erp_ventas/erp_ventas_remision_pdf",
    {
      ...logisticsContext(user, grants, companyId),
      folio,
      hide_prices: params.get("hide_prices") === "true"
    },
    "data"
  );
  return NextResponse.json(result.ok ? { ok: true, data: result.data } : { ok: false, error: result.error }, { status: result.ok ? 200 : 500 });
}
