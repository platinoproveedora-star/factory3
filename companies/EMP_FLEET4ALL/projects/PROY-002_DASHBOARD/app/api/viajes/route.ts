import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireFleetCompanyAccess } from "@/lib/access";
import { tripCreate, tripClose, tripKpis, tripManage } from "@/lib/fleet4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const s = new URL(req.url).searchParams;
  const empresaId = s.get("empresa_id");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await tripKpis({ empresa_id: empresaId });
  return NextResponse.json(result);
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const action = body.action || "create";
  const result = action === "close" ? await tripClose(body) : await tripCreate(body);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function PUT(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await tripManage({ ...body, action: "update" });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function DELETE(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const empresaId = String(body.empresa_id || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await tripManage({ ...body, action: "delete" });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
