import { NextRequest, NextResponse } from "next/server";
import { callSkill } from "@/lib/factory";
import { getSession } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const result = await callSkill("vertical_sat_conta4all/conta4all_sync_finalize", {
    managed_rfc_id: body.managed_rfc_id,
    rfc: body.rfc,
    id_solicitud: body.id_solicitud,
    tipo: body.tipo,
    paquetes: body.paquetes ?? [],
    cer_b64: body.cer_b64,
    key_b64: body.key_b64,
    key_password: body.key_password,
  });
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
