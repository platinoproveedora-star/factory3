import { NextRequest, NextResponse } from "next/server";
import { moduloCode } from "@/lib/auth";
import { callSkill } from "@/lib/factory";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.email || !body?.password || !body?.nombre) {
    return NextResponse.json({ ok: false, error: "nombre, email y password requeridos" }, { status: 400 });
  }
  const result = await callSkill<{ user_id?: string }>("vertical_auth_security/security_user_register", {
    email: body.email,
    password: body.password,
    password_confirm: body.password,
    nombre: body.nombre,
    modulo_code: moduloCode(),
    dry_run: false,
  });
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error }, { status: 400 });
  }
  if (!result.data?.user_id) {
    return NextResponse.json({ ok: false, error: "usuario creado sin user_id" }, { status: 500 });
  }
  const grant = await callSkill("vertical_auth_security/security_access_grant", {
    action: "create",
    user_id: result.data.user_id,
    modulo_code: moduloCode(),
    role: "owner",
    dry_run: false,
  });
  if (!grant.ok) {
    return NextResponse.json({ ok: false, error: grant.error || "no se pudo crear acceso al modulo" }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
