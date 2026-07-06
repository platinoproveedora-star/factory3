"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useCompany } from "@/lib/useCompany";

type TripKpis = {
  active_trips: number;
  utilidad_semana: number;
  utilidad_mes: number;
  profit_by_unit: Record<string, number>;
  profit_by_driver: Record<string, number>;
  top_expenses_by_type: { expense_type: string; amount: number }[];
};

const fmt = (n: number) => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: "MXN" });

const SECTIONS = [
  { href: "/dashboard/viajes", label: "Viajes" },
  { href: "/dashboard/gastos", label: "Gastos" },
  { href: "/dashboard/cobranza", label: "Cobranza" },
  { href: "/dashboard/cartaporte", label: "Carta Porte" },
  { href: "/dashboard/liquidaciones", label: "Liquidaciones" },
  { href: "/dashboard/combustible", label: "Combustible" },
  { href: "/dashboard/mantenimiento", label: "Mantenimiento" },
  { href: "/dashboard/cotizaciones", label: "Cotizaciones" },
];

export default function DashboardPage() {
  const { companies, selectedCompanyId, loading: loadingCompany } = useCompany();
  const [kpis, setKpis] = useState<TripKpis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedCompany = companies.find((c) => c.company_id === selectedCompanyId);

  useEffect(() => {
    if (!selectedCompanyId) return;
    setLoading(true);
    setError("");
    fetch(`/api/viajes?empresa_id=${encodeURIComponent(selectedCompanyId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) setKpis(d.data?.trip_kpis || null);
        else setError(d.error || "No se pudieron cargar los KPIs");
      })
      .catch(() => setError("No se pudieron cargar los KPIs"))
      .finally(() => setLoading(false));
  }, [selectedCompanyId]);

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Resumen</h1>
      <p className="text-muted text-sm mb-6">
        {selectedCompany?.name || selectedCompanyId || "Selecciona una empresa"}
      </p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12">
          <p className="text-muted">No tienes empresas activas para Fleet4All.</p>
        </div>
      ) : (
        <>
          {loading && <p className="text-muted text-sm mb-4">Cargando...</p>}
          {error && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm mb-4">{error}</div>}

          {kpis && (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
              <div className="card"><p className="text-muted text-sm">Viajes activos</p><p className="text-2xl font-bold mt-1">{kpis.active_trips}</p></div>
              <div className="card"><p className="text-muted text-sm">Utilidad semana</p><p className="text-2xl font-bold text-green-400 mt-1">{fmt(kpis.utilidad_semana)}</p></div>
              <div className="card"><p className="text-muted text-sm">Utilidad mes</p><p className="text-2xl font-bold text-green-400 mt-1">{fmt(kpis.utilidad_mes)}</p></div>
              <div className="card">
                <p className="text-muted text-sm">Top gasto</p>
                <p className="text-2xl font-bold mt-1">
                  {kpis.top_expenses_by_type[0] ? `${kpis.top_expenses_by_type[0].expense_type} · ${fmt(kpis.top_expenses_by_type[0].amount)}` : "-"}
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {SECTIONS.map((s) => (
              <Link key={s.href} href={s.href} className="card hover:border-slate-400 transition-colors text-center py-6">
                <p className="font-semibold">{s.label}</p>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
