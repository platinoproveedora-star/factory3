import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { COOKIE_NAME, cookieOptions, MODULO_CODE } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const rawLogin = String(body?.email || "").trim().toLowerCase();
  const compactLogin = rawLogin.replace(/\s+/g, "");
  const email = compactLogin === "admintotal" ? "admintotal@apps4all.local" : rawLogin;
  const password = String(body?.password || "");
  if (!email || !password) {
    return NextResponse.json({ ok: false, error: "email y password requeridos" }, { status: 400 });
  }
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
  const result = await callSkill("vertical_auth_security/security_user_login", {
    email,
    password,
    ip,
    modulo_code: MODULO_CODE,
    dry_run: false,
  });
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error }, { status: 401 });
  }
  const token = (result.data as { token: string }).token;
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE_NAME, token, cookieOptions(7200));
  return res;
}
