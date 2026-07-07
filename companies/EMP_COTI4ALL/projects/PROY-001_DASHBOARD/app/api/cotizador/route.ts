import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { fetchCatalog, getCompanyContextFromSession } from "@/lib/coti4all";
import { requireCompanyModuleGrant } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });

  const { searchParams } = new URL(req.url);
  try {
    const selectedCompanyId = searchParams.get("company_id") || user.company_id;
    try {
      await requireCompanyModuleGrant(user.sub, selectedCompanyId);
    } catch (error: any) {
      return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
    }
    const context = {
      ...(await getCompanyContextFromSession(user)),
      company_id: selectedCompanyId,
      schema: searchParams.get("schema") || process.env.COTI4ALL_SCHEMA || "coti4all",
    };
    const catalogRes = await fetchCatalog(context, searchParams.get("price_list_code") || undefined);

    if (!catalogRes.ok) {
      return NextResponse.json({ ok: false, catalog_error: catalogRes.error }, { status: 502 });
    }

    return NextResponse.json({
      ok: true,
      catalogo: catalogRes.data ?? [],
      quote: null,
      empresa: { company_id: selectedCompanyId, modulo_code: user.modulo_code },
    });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: e?.message || "composite fallo" }, { status: 500 });
  }
}
