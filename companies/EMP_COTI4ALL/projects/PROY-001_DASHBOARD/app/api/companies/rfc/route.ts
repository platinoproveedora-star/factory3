import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listGrants, updateCompanyRfc } from "@/lib/platform";

export const dynamic = "force-dynamic";
const MODULE_CODE = "coti4all_portal";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });

  const body = await req.json().catch(() => null);
  const companyId = String(body?.company_id || "").trim();
  const rfc = String(body?.rfc || "").trim().toUpperCase();
  if (!companyId) return NextResponse.json({ ok: false, error: "company_id requerido" }, { status: 400 });

  try {
    const grants = await listGrants(user.sub);
    const hasAccess = grants.some((grant) => grant.company_id === companyId && grant.modulo_code === MODULE_CODE);
    if (!hasAccess) return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });

    const company = await updateCompanyRfc(companyId, rfc);
    return NextResponse.json({ ok: true, company });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "No se pudo guardar el RFC" }, { status: 500 });
  }
}
