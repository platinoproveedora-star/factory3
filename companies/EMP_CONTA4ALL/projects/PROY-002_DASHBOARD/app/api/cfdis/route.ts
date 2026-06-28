import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { getSession } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const s = new URL(req.url).searchParams;
  const result = await callSkill("vertical_sat_conta4all/conta4all_cfdi_list", {
    managed_rfc_id: s.get("managed_rfc_id") ?? "",
    tipo: s.get("tipo") ?? undefined,
    fecha_inicio: s.get("fecha_inicio") ?? undefined,
    fecha_fin: s.get("fecha_fin") ?? undefined,
  });
  return NextResponse.json(result);
}
