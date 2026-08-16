import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const warehouseId = new URL(req.url).searchParams.get("warehouse_id") || undefined;
  const ctx = await resolveInventoryContext(user, warehouseId);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const limit = new URL(req.url).searchParams.get("limit") || "50";
  const result = await callSkill("vertical_erp_inventory/erp_inventory_kardex_list", {
    ...ctx.data,
    limit: Number(limit),
    warehouse_id: warehouseId
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const ctx = await resolveInventoryContext(user, body.warehouse_id);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const result = await callSkill<{ movement: any }>("vertical_erp_inventory/erp_inventory_kardex_save", {
    ...ctx.data,
    ...body,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}
