import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type BulkItem = { product_name: string; sku?: string };

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const ctx = await resolveInventoryContext(user);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const body = await req.json().catch(() => ({}));
  const items: BulkItem[] = Array.isArray(body.items) ? body.items : [];
  if (!items.length) return NextResponse.json({ ok: false, error: "items requerido" }, { status: 400 });

  const shared = {
    category: body.category || undefined,
    category_2: body.category_2 || undefined,
    brand: body.brand || undefined,
    unit: body.unit || "pieza",
    min_stock: body.min_stock ?? 0
  };

  const results: { product_name: string; sku?: string; ok: boolean; product_id?: string; folio?: string; error?: string }[] = [];
  for (const item of items) {
    const result = await callSkill<{ product: any }>("vertical_erp_inventory/erp_inventory_product_save", {
      ...ctx.data,
      product_name: item.product_name,
      sku: item.sku,
      ...shared,
      dry_run: false
    });
    if (!result.ok) {
      results.push({ product_name: item.product_name, sku: item.sku, ok: false, error: result.error });
    } else {
      results.push({
        product_name: item.product_name,
        sku: item.sku,
        ok: true,
        product_id: result.data?.product?.id,
        folio: result.data?.product?.folio
      });
    }
  }

  return NextResponse.json({ ok: true, data: { results } });
}
