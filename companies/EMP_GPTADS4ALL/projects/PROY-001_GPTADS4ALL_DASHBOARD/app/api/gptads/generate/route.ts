import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { buildCampaign } from "@/lib/gptads4all";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => null);
  const productName = body?.product_name || body?.brief_analysis?.product_name;
  const description = body?.description || body?.brief_analysis?.optimized_description || body?.brief_analysis?.prompt_optimized;
  if (!productName || !description) {
    return NextResponse.json({ ok: false, error: "Producto y descripcion requeridos" }, { status: 400 });
  }
  try {
    const data = await buildCampaign(user, body);
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "No se pudo generar campana" }, { status: 500 });
  }
}
