import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { MODULO_CODE } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password || !body?.nombre) {
    return NextResponse.json({ ok: false, error: "nombre, email y password requeridos" }, { status: 400 });
  }
  const result = await callSkill("vertical_auth_security/security_user_register", {
    email: body.email,
    password: body.password,
    password_confirm: body.password,
    nombre: body.nombre,
    modulo_code: MODULO_CODE,
    dry_run: false,
  });
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
