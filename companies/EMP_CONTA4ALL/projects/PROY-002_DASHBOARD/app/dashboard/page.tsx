import { getSession } from "@/lib/auth";
import { callSkill } from "@/lib/factory";
import Link from "next/link";
import OverviewChart from "./overview-chart";

async function getCfdis(managed_rfc_id: string) {
  const hoy = new Date();
  const inicio = new Date(hoy.getFullYear(), hoy.getMonth() - 2, 1);
  return callSkill("vertical_sat_conta4all/conta4all_cfdi_list", {
    managed_rfc_id,
    fecha_inicio: inicio.toISOString().slice(0, 10),
    fecha_fin: hoy.toISOString().slice(0, 10),
    dry_run: false,
  });
}

async function getRfcs(user_id: string) {
  return callSkill("vertical_auth_security/security_managed_rfc", {
    action: "list",
    user_id,
    modulo_code: "conta4all",
    dry_run: false,
  });
}

export default async function DashboardPage() {
  const user = await getSession();
  if (!user) return null;

  const rfcsRes = await getRfcs(user.sub);
  const rfcs: Array<{ id: string; rfc: string; label: string }> = rfcsRes.ok
    ? (rfcsRes.data as { rfcs: Array<{ id: string; rfc: string; label: string }> })?.rfcs ?? []
    : [];

  const firstRfc = rfcs[0];
  let cfdis: Array<Record<string, unknown>> = [];
  let ingresos = 0;
  let egresos = 0;
  let numCfdis = 0;

  if (firstRfc) {
    const cRes = await getCfdis(firstRfc.id);
    if (cRes.ok) {
      cfdis = ((cRes.data as { cfdis: Array<Record<string, unknown>> })?.cfdis ?? []) as Array<Record<string, unknown>>;
      numCfdis = cfdis.length;
      for (const c of cfdis) {
        if (c.tipo === "I") ingresos += Number(c.total) || 0;
        else if (c.tipo === "E") egresos += Number(c.total) || 0;
      }
    }
  }

  const fmt = (n: number) =>
    n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Resumen</h1>
      <p className="text-muted text-sm mb-6">Últimos 3 meses</p>

      {rfcs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-muted mb-3">Aún no tienes RFCs registrados</p>
          <Link href="/dashboard/rfcs" className="btn-primary">
            Agregar RFC
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="card">
              <p className="text-muted text-sm">Ingresos</p>
              <p className="text-2xl font-bold text-green-400 mt-1">{fmt(ingresos)}</p>
            </div>
            <div className="card">
              <p className="text-muted text-sm">Egresos</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{fmt(egresos)}</p>
            </div>
            <div className="card">
              <p className="text-muted text-sm">CFDIs</p>
              <p className="text-2xl font-bold mt-1">{numCfdis}</p>
            </div>
          </div>
          <div className="card mb-6">
            <p className="text-sm text-muted mb-3">RFC activo: <span className="text-white font-mono">{firstRfc.rfc}</span></p>
            <OverviewChart cfdis={cfdis} />
          </div>
          <div className="flex gap-3">
            <Link href="/dashboard/sincronizar" className="btn-primary">
              Sincronizar SAT
            </Link>
            <Link href="/dashboard/cfdis" className="btn-ghost">
              Ver todos los CFDIs
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
