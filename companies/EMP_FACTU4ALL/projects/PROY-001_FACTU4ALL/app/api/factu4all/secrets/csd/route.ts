import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { csdStatus, saveCsd } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const rfc = (req.nextUrl.searchParams.get("rfc") || "").toUpperCase();
  if (!rfc) return NextResponse.json({ ok: false, error: "rfc requerido" }, { status: 400 });
  const result = await csdStatus(user.company_id, rfc);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const body = await req.json().catch(() => ({}));
  const rfc = String(body.rfc || "").toUpperCase();
  if (!rfc || !body.cer_b64 || !body.key_b64 || !body.password) {
    return NextResponse.json({ ok: false, error: "rfc, cer_b64, key_b64 y password requeridos" }, { status: 400 });
  }
  const result = await saveCsd(user.company_id, rfc, {
    cer_b64: body.cer_b64,
    key_b64: body.key_b64,
    password: body.password,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
