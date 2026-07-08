import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { requireFleetCompanyAccess } from "@/lib/access";
import { expenseCapture, expenseManage } from "@/lib/fleet4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const params = new URL(req.url).searchParams;
  const empresaId = String(params.get("empresa_id") || "");
  if (!empresaId) return NextResponse.json({ ok: false, error: "empresa_id requerido" }, { status: 400 });
  if (!(await requireFleetCompanyAccess(user.sub, empresaId))) {
    return NextResponse.json({ ok: false, error: "Sin acceso a esta empresa" }, { status: 403 });
  }
  const result = await expenseManage({
    action: "list",
    empresa_id: empresaId,
    from: params.get("from") || undefined,
    to: params.get("to") || undefined,
    trip_folio: params.get("trip_folio") || undefined,
    limit: Number(params.get("limit") || 100),
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
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
  const result = await expenseCapture(body);
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
  const result = await expenseManage({ ...body, action: "update", dry_run: false });
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
  const result = await expenseManage({ ...body, action: "delete", dry_run: false });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
