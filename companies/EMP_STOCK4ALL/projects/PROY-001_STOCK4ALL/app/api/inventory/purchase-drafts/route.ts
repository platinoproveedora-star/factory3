import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { resolveInventoryContext } from "@/lib/inventory";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const result = await callSkill<{ drafts: any[] }>("vertical_erp_compras/erp_compras_purchase_draft", {
    action: "list",
    company_id: user.company_id
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "sin sesion" }, { status: 401 });

  const ctx = await resolveInventoryContext(user);
  if (!ctx.ok) return NextResponse.json({ ok: false, error: ctx.error }, { status: 409 });

  const body = await req.json().catch(() => ({}));
  const result = await callSkill<{ draft: any }>("vertical_erp_compras/erp_compras_purchase_draft", {
    action: "upload_extract",
    company_id: ctx.data.company_id,
    source_schema: ctx.data.schema,
    source_project_code: ctx.data.project_code,
    warehouse_id: ctx.data.warehouse_id,
    content_b64: body.content_b64,
    media_type: body.media_type,
    filename: body.filename,
    dry_run: false
  });
  if (!result.ok) return NextResponse.json({ ok: false, error: result.error }, { status: 500 });

  return NextResponse.json({ ok: true, data: result.data });
}
