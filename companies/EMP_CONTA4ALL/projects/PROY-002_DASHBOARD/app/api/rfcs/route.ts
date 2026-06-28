import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { getSession, MODULO_CODE } from "@/lib/auth";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const result = await callSkill("vertical_auth_security/security_managed_rfc", {
    action: "list",
    user_id: user.sub,
    modulo_code: MODULO_CODE,
    dry_run: false,
  });
  return NextResponse.json(result);
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const result = await callSkill("vertical_auth_security/security_managed_rfc", {
    action: "create",
    user_id: user.sub,
    rfc: body.rfc,
    label: body.label ?? "",
    modulo_code: MODULO_CODE,
    dry_run: false,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function DELETE(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const id = new URL(req.url).searchParams.get("id");
  if (!id) return NextResponse.json({ ok: false, error: "id requerido" }, { status: 400 });
  const result = await callSkill("vertical_auth_security/security_managed_rfc", {
    action: "delete",
    id,
    user_id: user.sub,
    modulo_code: MODULO_CODE,
    dry_run: false,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
