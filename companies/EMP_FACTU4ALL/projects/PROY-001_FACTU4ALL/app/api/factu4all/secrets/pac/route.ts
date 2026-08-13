import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";
import { pacCredentialsStatus, savePacCredentials } from "@/lib/factu4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, "factu4all");
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const pacProvider = req.nextUrl.searchParams.get("pac_provider") || "facturama";
  const result = await pacCredentialsStatus(user.company_id, pacProvider);
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
  const pacProvider = String(body.pac_provider || "facturama");
  if (!body.user || !body.password || !body.url) {
    return NextResponse.json({ ok: false, error: "user, password y url requeridos" }, { status: 400 });
  }
  const result = await savePacCredentials(user.company_id, pacProvider, {
    user: body.user,
    password: body.password,
    url: body.url,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
