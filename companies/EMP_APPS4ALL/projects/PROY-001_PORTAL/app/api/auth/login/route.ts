import { NextRequest, NextResponse } from "next/server";
import { cookieOptions, COOKIE_NAME, signSession } from "@/lib/auth";
import { callSkill } from "@/lib/factory";
import { companyName, findUserByEmail, listCompanies, listGrants, logLoginAttempt } from "@/lib/platform";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const rawLogin = String(body?.email || "").trim().toLowerCase();
  const email = rawLogin === "admintotal" ? "admintotal@apps4all.local" : rawLogin;
  const password = String(body?.password || "");
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
  if (!email || !password) {
    return NextResponse.json({ ok: false, error: "email y password requeridos" }, { status: 400 });
  }

  try {
    const skillResult = await callSkill("vertical_auth_security/security_user_login", {
      email,
      password,
      ip,
      modulo_code: "apps4all_portal",
      dry_run: false,
    });
    if (!skillResult.ok) {
      await logLoginAttempt(email, ip, false);
      return NextResponse.json({ ok: false, error: "Credenciales incorrectas" }, { status: 401 });
    }
    const user = await findUserByEmail(email);
    if (!user) {
      return NextResponse.json({ ok: false, error: "Usuario no encontrado" }, { status: 401 });
    }
    const grants = await listGrants(user.id);
    if (!grants.length) {
      await logLoginAttempt(email, ip, false);
      return NextResponse.json({ ok: false, error: "Usuario sin modulos activos" }, { status: 403 });
    }
    const companies = await listCompanies(Array.from(new Set(grants.map((grant) => grant.company_id))));
    const preferred = grants.find((grant) => grant.modulo_code === "apps4all_portal") || grants[0];
    const token = await signSession({
      sub: user.id,
      email: user.email,
      company_id: preferred.company_id,
      company_name: companyName(companies, preferred.company_id),
      modulo_code: preferred.modulo_code,
      role: preferred.role,
      grant_id: preferred.id,
      plan_code: preferred.plan_code || "manual",
      subscription_status: preferred.subscription_status || preferred.status || "manual"
    });
    await logLoginAttempt(email, ip, true);
    const res = NextResponse.json({ ok: true });
    res.cookies.set(COOKIE_NAME, token, cookieOptions(7200));
    return res;
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "login fallo" }, { status: 500 });
  }
}
