import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { COOKIE_NAME, cookieOptions, moduloCode } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password) {
    return NextResponse.json({ ok: false, error: "email y password requeridos" }, { status: 400 });
  }
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
  const result = await callSkill<{ token: string }>("vertical_auth_security/security_user_login", {
    email: body.email,
    password: body.password,
    ip,
    modulo_code: moduloCode(),
    dry_run: false,
  });
  if (!result.ok || !result.data?.token) {
    return NextResponse.json({ ok: false, error: result.error || "login invalido" }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE_NAME, result.data.token, cookieOptions(7200));
  return res;
}
