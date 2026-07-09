import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { saveCatalogItemCost } from "@/lib/coti4all";
import { requireCompanyModuleGrant } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });

  try {
    await requireCompanyModuleGrant(user.sub, empresaId);
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }

  const result = await saveCatalogItemCost({
    schema: process.env.COTI4ALL_SCHEMA || "coti4all",
    empresa_id: empresaId,
    sku: body.sku,
    nombre: body.nombre,
    costo: body.costo,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
