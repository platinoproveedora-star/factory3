import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const result = await callSkill<{ draft: any }>("vertical_erp_compras/erp_compras_purchase_draft", {
    action: "update",
    id,
    company_id: user.company_id,
    extracted_json: body.extracted_json,
    notes: body.notes,
    warehouse_id: body.warehouse_id,
    status: body.status,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const { id } = await params;
  const result = await callSkill("vertical_erp_compras/erp_compras_purchase_draft", {
    action: "delete",
    id,
    company_id: user.company_id,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true });
}
