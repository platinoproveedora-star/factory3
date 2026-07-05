import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { analyzeBrief } from "@/lib/gptads4all";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => null);
  if (!body?.raw_brief && !body?.description) {
    return NextResponse.json({ ok: false, error: "Descripcion general requerida" }, { status: 400 });
  }
  try {
    const data = await analyzeBrief(user, body);
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "No se pudo analizar el brief" }, { status: 500 });
  }
}
