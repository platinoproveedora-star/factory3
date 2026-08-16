import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, cookieOptions, getSession, signSession } from "@/lib/auth";
import { companyName, listCompanies, listGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";
const MODULE_CODE = process.env.MODULE_CODE || "factu4all";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const companyId = String(body.company_id || "");
  if (!companyId) return NextResponse.json({ ok: false, error: "company_id requerido" }, { status: 400 });

  const grants = await listGrants(user.sub);
  const grant = grants.find((row) => row.company_id === companyId && row.modulo_code === MODULE_CODE);
  if (!grant) return NextResponse.json({ ok: false, error: "Sin acceso a esa empresa" }, { status: 403 });

  const companies = await listCompanies([companyId]);
  const token = await signSession({
    sub: user.sub,
    email: user.email,
    company_id: grant.company_id,
    company_name: companyName(companies, grant.company_id),
    modulo_code: grant.modulo_code,
    role: grant.role,
    grant_id: grant.id,
    plan_code: grant.plan_code || "manual",
    subscription_status: grant.subscription_status || grant.status || "manual",
  });

  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE_NAME, token, cookieOptions(7200));
  return res;
}
