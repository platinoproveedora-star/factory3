import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  await callSkill("vertical_erp_inventory/erp_inventory_warehouse_manage", {
    action: "ensure_default",
    company_id: user.company_id,
    dry_run: false
  });

  const result = await callSkill<{ warehouses: any[] }>("vertical_erp_inventory/erp_inventory_warehouse_manage", {
    action: "list",
    company_id: user.company_id
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const result = await callSkill<{ warehouse: any }>("vertical_erp_inventory/erp_inventory_warehouse_manage", {
    action: "create",
    company_id: user.company_id,
    code: body.code,
    name: body.name,
    is_default: false,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}
