import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const ctx = await resolveInventoryContext(user);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const result = await callSkill<{ customers?: any[]; suppliers?: any[] }>(
    "vertical_erp_inventory/erp_inventory_dashboard_data",
    { ...ctx.data, action: "dashboard" }
  );
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  const suppliers = result.data?.suppliers || [];
  const customers = result.data?.customers || [];
  return NextResponse.json({ ok: true, data: { suppliers, customers } });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const ctx = await resolveInventoryContext(user);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const body = await req.json().catch(() => ({}));
  const result = await callSkill<{ party: any }>("vertical_erp_inventory/erp_inventory_party_save", {
    ...ctx.data,
    ...body,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}
