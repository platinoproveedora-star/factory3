import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const ctx = await resolveInventoryContext(user, body.warehouse_id);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const result = await callSkill<{ purchase: any; movements: any[] }>("vertical_erp_compras/erp_compras_purchase_draft", {
    action: "confirm",
    id,
    company_id: ctx.data.company_id,
    source_schema: ctx.data.schema,
    source_project_code: ctx.data.project_code,
    warehouse_id: ctx.data.warehouse_id,
    supplier_id: body.supplier_id,
    movement_date: body.movement_date,
    external_folio: body.external_folio,
    paid_amount: body.paid_amount,
    notes: body.notes,
    items: body.items,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}
