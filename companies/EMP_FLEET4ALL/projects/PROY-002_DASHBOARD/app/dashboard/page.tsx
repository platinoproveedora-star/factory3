"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useCompany } from "@/lib/useCompany";

type Summary = {
  period: { from?: string; to?: string };
  active_trips: number;
  trips_missing_resources: number;
  period_profit: number;
  overdue_receivables: number;
  overdue_receivables_count: number;
  maintenance_due_soon: number;
  fuel_alerts: number;
  currency: string;
};

type Health = {
  module: string;
  status: "ok" | "warning" | "alert";
  count: number;
  href: string;
};

type CriticalItem = {
  type: string;
  severity: "ok" | "warning" | "alert";
  title: string;
  description?: string;
  href: string;
  ref?: string;
};

type Snapshot = {
  summary: Summary;
  health: Health[];
  critical_items: CriticalItem[];
};

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

function monthStart() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function sevenDaysAgo() {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().slice(0, 10);
}

function badgeClass(status: string) {
  if (status === "alert") return "badge-red";
  if (status === "warning") return "badge-yellow";
  return "badge-green";
}

export default function DashboardPage() {
  const { companies, selectedCompanyId, loading: loadingCompany } = useCompany();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [periodMode, setPeriodMode] = useState<"month" | "week" | "custom">("month");
  const [customFrom, setCustomFrom] = useState(monthStart());
  const [customTo, setCustomTo] = useState(today());
  const selectedCompany = companies.find((company) => company.company_id === selectedCompanyId);

  const period = useMemo(() => {
    if (periodMode === "week") return { from: sevenDaysAgo(), to: today() };
    if (periodMode === "custom") return { from: customFrom, to: customTo };
    return { from: monthStart(), to: today() };
  }, [periodMode, customFrom, customTo]);

  useEffect(() => {
    if (!selectedCompanyId) return;
    const qs = new URLSearchParams({
      empresa_id: selectedCompanyId,
      from: period.from,
      to: period.to,
    });
    setLoading(true);
    setError("");
    fetch(`/api/resumen?${qs.toString()}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.ok) setSnapshot(data.data || null);
        else setError(data.error || "No se pudo cargar el resumen");
      })
      .catch(() => setError("No se pudo cargar el resumen"))
      .finally(() => setLoading(false));
  }, [selectedCompanyId, period]);

  if (loadingCompany) return null;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-xl font-bold mb-1">Resumen</h1>
          <p className="text-muted text-sm">
            {selectedCompany?.name || selectedCompanyId || "Selecciona una empresa"}
          </p>
        </div>

        {selectedCompanyId ? (
          <div className="flex flex-wrap items-end gap-2">
            <div className="inline-flex rounded-md border border-border overflow-hidden">
              <button type="button" className={periodMode === "month" ? "btn-primary rounded-none py-1.5" : "btn-ghost rounded-none py-1.5"} onClick={() => setPeriodMode("month")}>Mes</button>
              <button type="button" className={periodMode === "week" ? "btn-primary rounded-none py-1.5" : "btn-ghost rounded-none py-1.5"} onClick={() => setPeriodMode("week")}>7 dias</button>
              <button type="button" className={periodMode === "custom" ? "btn-primary rounded-none py-1.5" : "btn-ghost rounded-none py-1.5"} onClick={() => setPeriodMode("custom")}>Rango</button>
            </div>
            {periodMode === "custom" ? (
              <>
                <input type="date" className="input w-36" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} />
                <input type="date" className="input w-36" value={customTo} onChange={(event) => setCustomTo(event.target.value)} />
              </>
            ) : null}
          </div>
        ) : null}
      </div>

      {!selectedCompanyId ? (
        <div className="card text-center py-12">
          <p className="text-muted">No tienes empresas activas para Fleet4All.</p>
        </div>
      ) : (
        <>
          {loading && <p className="text-muted text-sm mb-4">Cargando...</p>}
          {error && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm mb-4">{error}</div>}

          {snapshot ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
                <div className="card">
                  <p className="text-muted text-sm">Utilidad periodo</p>
                  <p className="text-2xl font-bold text-green-400 mt-1">{fmt(snapshot.summary.period_profit, snapshot.summary.currency)}</p>
                </div>
                <div className="card">
                  <p className="text-muted text-sm">Viajes activos</p>
                  <p className="text-2xl font-bold mt-1">{snapshot.summary.active_trips}</p>
                </div>
                <div className="card">
                  <p className="text-muted text-sm">CxC vencida</p>
                  <p className="text-2xl font-bold text-red-300 mt-1">{fmt(snapshot.summary.overdue_receivables, snapshot.summary.currency)}</p>
                  <p className="text-muted text-xs mt-1">{snapshot.summary.overdue_receivables_count} cuentas</p>
                </div>
                <div className="card">
                  <p className="text-muted text-sm">Alertas operativas</p>
                  <p className="text-2xl font-bold mt-1">{snapshot.summary.trips_missing_resources + snapshot.summary.maintenance_due_soon + snapshot.summary.fuel_alerts}</p>
                  <p className="text-muted text-xs mt-1">viajes, mantenimiento y fuel</p>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
                <div className="card">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <h2 className="font-semibold">Pendientes criticos</h2>
                    <span className="text-muted text-xs">{snapshot.summary.period.from} a {snapshot.summary.period.to}</span>
                  </div>
                  {snapshot.critical_items.length ? (
                    <div className="space-y-2">
                      {snapshot.critical_items.map((item, index) => (
                        <Link key={`${item.type}-${item.ref || index}`} href={item.href} className="block rounded-md border border-border px-3 py-2 hover:border-slate-400 transition-colors">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium text-sm">{item.title}</p>
                              {item.description ? <p className="text-muted text-xs mt-0.5">{item.description}</p> : null}
                            </div>
                            <span className={badgeClass(item.severity)}>{item.severity}</span>
                          </div>
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-md border border-border px-3 py-6 text-center">
                      <p className="text-muted text-sm">Sin pendientes criticos para este periodo.</p>
                    </div>
                  )}
                </div>

                <div className="card">
                  <h2 className="font-semibold mb-4">Salud por modulo</h2>
                  <div className="space-y-2">
                    {snapshot.health.map((row) => (
                      <Link key={row.module} href={row.href} className="flex items-center justify-between rounded-md border border-border px-3 py-2 hover:border-slate-400 transition-colors">
                        <div>
                          <p className="font-medium text-sm">{row.module}</p>
                          <p className="text-muted text-xs">{row.count} pendientes</p>
                        </div>
                        <span className={badgeClass(row.status)}>{row.status}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
