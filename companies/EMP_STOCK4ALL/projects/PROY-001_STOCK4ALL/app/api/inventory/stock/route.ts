import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const ctx = await resolveInventoryContext(user);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const status = new URL(req.url).searchParams.get("status");
  const activeStatus = status === "inactive" ? "inactive" : "active";

  const result = await callSkill("vertical_erp_inventory/erp_inventory_current_stock_report", {
    ...ctx.data,
    active_status: activeStatus
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data, context: ctx.data });
}
