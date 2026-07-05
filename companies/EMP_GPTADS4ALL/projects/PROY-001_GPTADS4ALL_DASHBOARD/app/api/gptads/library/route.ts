import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listLibrary } from "@/lib/gptads4all";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  try {
    const data = await listLibrary(user, body || {});
    return NextResponse.json({ ok: true, data });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "No se pudo cargar biblioteca" }, { status: 500 });
  }
}
