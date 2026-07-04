import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, cookieOptions, signSession } from "@/lib/auth";
import { findUserByEmail, listGrants, listCompanies, logLoginAttempt } from "@/lib/platform";

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
    const skillResult = await (await import("@/lib/factory")).callSkill<any>("vertical_auth_security/security_user_login", {
      email,
      password,
      ip,
      modulo_code: "coti4all_portal",
      dry_run: false,
    });
    if (!skillResult.ok) {
      await logLoginAttempt(email, ip, false);
      return NextResponse.json({ ok: false, error: "Credenciales incorrectas" }, { status: 401 });
    }
    const user = await findUserByEmail(email);
    if (!user) return NextResponse.json({ ok: false, error: "Usuario no encontrado" }, { status: 401 });

    const grants = await listGrants(user.id);
    if (!grants.length) {
      await logLoginAttempt(email, ip, false);
      return NextResponse.json({ ok: false, error: "Usuario sin modulos activos" }, { status: 403 });
    }
    const companies = await listCompanies(Array.from(new Set(grants.map((grant) => grant.company_id))));
    const preferred = grants.find((grant) => grant.modulo_code === "coti4all_portal") || grants.find((grant) => grant.company_id === (user as any)?.company_id) || grants[0];
    const chosen = preferred || grants[0];
    if (!chosen) return NextResponse.json({ ok: false, error: "Grant invalido" }, { status: 403 });

    const token = await signSession({
      sub: user.id,
      email: user.email,
      company_id: chosen.company_id,
      company_name: (await import("@/lib/platform")).companyName(companies, chosen.company_id),
      modulo_code: chosen.modulo_code,
      role: chosen.role,
      grant_id: chosen.id,
      plan_code: chosen.plan_code || "manual",
      subscription_status: chosen.subscription_status || chosen.status || "manual"
    });
    await logLoginAttempt(email, ip, true);
    const res = NextResponse.json({ ok: true });
    res.cookies.set(COOKIE_NAME, token, cookieOptions(7200));
    return res;
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "login fallo" }, { status: 500 });
  }
}
