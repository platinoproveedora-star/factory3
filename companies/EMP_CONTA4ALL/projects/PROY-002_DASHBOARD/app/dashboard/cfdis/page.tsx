"use client";
import { useState, useEffect, useCallback } from "react";
import clsx from "clsx";

type Cfdi = Record<string, string | number | null | undefined>;

interface Rfc { id: string; rfc: string; label?: string; }

const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const COLUMN_LABELS: Record<string, string> = {
  uuid_cfdi: "UUID",
  tipo: "Tipo",
  rfc_emisor: "RFC emisor",
  nombre_emisor: "Emisor",
  rfc_receptor: "RFC receptor",
  nombre_receptor: "Receptor",
  fecha_emision: "Fecha emision",
  fecha_timbrado: "Fecha timbrado",
  total: "Total",
  subtotal: "Subtotal",
  descuento: "Descuento",
  moneda: "Moneda",
  tipo_comprobante: "Tipo comprobante",
  metodo_pago: "Metodo pago",
  forma_pago: "Forma pago",
  uso_cfdi: "Uso CFDI",
};

const fmtMoney = (n: unknown, m = "MXN") =>
  Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: m || "MXN" });

const asText = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "-";
  return String(value);
};

const tipoLabel = (tipo: unknown) => String(tipo) === "E" ? "Ingreso" : "Egreso";
const tipoBadge = (tipo: unknown) => String(tipo) === "E" ? "badge-green" : "badge-red";

function sortedColumns(rows: Cfdi[]) {
  const preferred = [
    "fecha_emision", "tipo", "uuid_cfdi", "rfc_emisor", "nombre_emisor",
    "rfc_receptor", "nombre_receptor", "subtotal", "descuento", "total",
    "moneda", "tipo_comprobante", "metodo_pago", "forma_pago", "uso_cfdi",
    "fecha_timbrado",
  ];
  const found = new Set(rows.flatMap((row) => Object.keys(row)));
  return [
    ...preferred.filter((key) => found.has(key)),
    ...Array.from(found).filter((key) => !preferred.includes(key)).sort(),
  ];
}

function monthKey(row: Cfdi) {
  return String(row.fecha_emision || "").slice(0, 7);
}

function groupByMonth(rows: Cfdi[]) {
  return rows.reduce<Record<string, Cfdi[]>>((acc, row) => {
    const key = monthKey(row);
    if (!key) return acc;
    acc[key] = acc[key] || [];
    acc[key].push(row);
    return acc;
  }, {});
}

export default function CfdisPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [activeTab, setActiveTab] = useState<"buscar" | "fiscal">("buscar");
  const [filters, setFilters] = useState({
    managed_rfc_id: "",
    tipo: "",
    fecha_inicio: "",
    fecha_fin: "",
  });
  const [fiscal, setFiscal] = useState({
    managed_rfc_id: "",
    year: String(new Date().getFullYear()),
  });
  const [cfdis, setCfdis] = useState<Cfdi[]>([]);
  const [fiscalCfdis, setFiscalCfdis] = useState<Cfdi[]>([]);
  const [loading, setLoading] = useState(false);
  const [fiscalLoading, setFiscalLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [fiscalSearched, setFiscalSearched] = useState(false);
  const [error, setError] = useState("");
  const [fiscalError, setFiscalError] = useState("");

  useEffect(() => {
    fetch("/api/rfcs").then((r) => r.json()).then((d) => {
      if (d.ok) {
        const rows = d.data?.rfcs ?? [];
        setRfcs(rows);
        if (rows.length === 1) {
          setFilters((f) => ({ ...f, managed_rfc_id: rows[0].id }));
          setFiscal((f) => ({ ...f, managed_rfc_id: rows[0].id }));
        }
      }
    });
  }, []);

  const fetchCfdis = useCallback(async (params: Record<string, string>) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    const res = await fetch(`/api/cfdis?${qs}`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Error consultando CFDIs");
    return (data.data?.cfdis ?? []) as Cfdi[];
  }, []);

  const handleSearch = useCallback(async () => {
    if (!filters.managed_rfc_id) return;
    setLoading(true); setSearched(true); setError("");
    try {
      setCfdis(await fetchCfdis({ ...filters, limit: "5000" }));
    } catch (err) {
      setCfdis([]);
      setError(err instanceof Error ? err.message : "Error consultando CFDIs");
    } finally {
      setLoading(false);
    }
  }, [fetchCfdis, filters]);

  const handleFiscalSearch = useCallback(async () => {
    if (!fiscal.managed_rfc_id || !fiscal.year) return;
    setFiscalLoading(true); setFiscalSearched(true); setFiscalError("");
    try {
      setFiscalCfdis(await fetchCfdis({
        managed_rfc_id: fiscal.managed_rfc_id,
        fecha_inicio: `${fiscal.year}-01-01`,
        fecha_fin: `${fiscal.year}-12-31`,
        limit: "10000",
      }));
    } catch (err) {
      setFiscalCfdis([]);
      setFiscalError(err instanceof Error ? err.message : "Error consultando ano fiscal");
    } finally {
      setFiscalLoading(false);
    }
  }, [fetchCfdis, fiscal]);

  const columns = sortedColumns(cfdis);
  const months = groupByMonth(fiscalCfdis);
  const monthKeys = Object.keys(months).sort().reverse();
  const fiscalTotals = fiscalCfdis.reduce<{ ingresos: number; egresos: number }>(
    (acc, row) => {
      const total = Number(row.total || 0);
      if (row.tipo === "E") acc.ingresos += total;
      if (row.tipo === "R") acc.egresos += total;
      return acc;
    },
    { ingresos: 0, egresos: 0 }
  );

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">CFDIs</h1>
      <p className="text-muted text-sm mb-6">Ingresos y egresos sincronizados del SAT</p>

      <div className="flex gap-2 mb-5">
        <button className={activeTab === "buscar" ? "btn-primary" : "btn-ghost"} onClick={() => setActiveTab("buscar")}>
          Buscador
        </button>
        <button className={activeTab === "fiscal" ? "btn-primary" : "btn-ghost"} onClick={() => setActiveTab("fiscal")}>
          Año fiscal
        </button>
      </div>

      {activeTab === "buscar" && (
        <>
          <div className="card mb-6">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="col-span-2 sm:col-span-1">
                <label className="label">RFC</label>
                <select className="input" value={filters.managed_rfc_id} onChange={(e) => setFilters((f) => ({ ...f, managed_rfc_id: e.target.value }))}>
                  <option value="">Selecciona RFC</option>
                  {rfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}{r.label ? ` - ${r.label}` : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Tipo</label>
                <select className="input" value={filters.tipo} onChange={(e) => setFilters((f) => ({ ...f, tipo: e.target.value }))}>
                  <option value="">Todos</option>
                  <option value="E">Ingresos</option>
                  <option value="R">Egresos</option>
                </select>
              </div>
              <div>
                <label className="label">Desde</label>
                <input type="date" className="input" value={filters.fecha_inicio} onChange={(e) => setFilters((f) => ({ ...f, fecha_inicio: e.target.value }))} />
              </div>
              <div>
                <label className="label">Hasta</label>
                <input type="date" className="input" value={filters.fecha_fin} onChange={(e) => setFilters((f) => ({ ...f, fecha_fin: e.target.value }))} />
              </div>
            </div>
            <button className="btn-primary mt-3" onClick={handleSearch} disabled={!filters.managed_rfc_id || loading}>
              {loading ? "Buscando..." : "Buscar"}
            </button>
          </div>

          {loading && <p className="text-muted text-sm">Cargando...</p>}
          {!loading && error && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm">{error}</div>}
          {!loading && searched && !error && cfdis.length === 0 && (
            <div className="card text-center py-12"><p className="text-muted">No se encontraron CFDIs con esos filtros</p></div>
          )}

          {!loading && cfdis.length > 0 && (
            <>
              <p className="text-muted text-sm mb-3">{cfdis.length} CFDIs encontrados</p>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-xs">
                  <thead className="bg-card text-muted border-b border-border">
                    <tr>
                      {columns.map((col) => (
                        <th key={col} className="text-left px-3 py-3 whitespace-nowrap">{COLUMN_LABELS[col] ?? col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cfdis.map((row) => (
                      <tr key={String(row.uuid_cfdi)} className="border-b border-border/50 hover:bg-card/60 transition-colors">
                        {columns.map((col) => (
                          <td key={col} className={clsx("px-3 py-2 whitespace-nowrap", col === "total" && "text-right font-mono")}>
                            {col === "tipo" ? (
                              <span className={tipoBadge(row[col])}>{tipoLabel(row[col])}</span>
                            ) : col === "total" || col === "subtotal" || col === "descuento" ? (
                              fmtMoney(row[col], String(row.moneda || "MXN"))
                            ) : (
                              asText(row[col])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {activeTab === "fiscal" && (
        <>
          <div className="card mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="label">RFC</label>
                <select className="input" value={fiscal.managed_rfc_id} onChange={(e) => setFiscal((f) => ({ ...f, managed_rfc_id: e.target.value }))}>
                  <option value="">Selecciona RFC</option>
                  {rfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}{r.label ? ` - ${r.label}` : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Año</label>
                <input className="input" inputMode="numeric" value={fiscal.year} onChange={(e) => setFiscal((f) => ({ ...f, year: e.target.value }))} />
              </div>
              <div className="flex items-end">
                <button className="btn-primary w-full" onClick={handleFiscalSearch} disabled={!fiscal.managed_rfc_id || !fiscal.year || fiscalLoading}>
                  {fiscalLoading ? "Buscando..." : "Buscar año fiscal"}
                </button>
              </div>
            </div>
          </div>

          {fiscalLoading && <p className="text-muted text-sm">Cargando...</p>}
          {!fiscalLoading && fiscalError && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm">{fiscalError}</div>}
          {!fiscalLoading && fiscalSearched && !fiscalError && fiscalCfdis.length === 0 && (
            <div className="card text-center py-12"><p className="text-muted">No hay CFDIs para ese año</p></div>
          )}

          {!fiscalLoading && fiscalCfdis.length > 0 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="card"><p className="text-muted text-sm">Ingresos año</p><p className="text-green-400 text-xl font-bold">{fmtMoney(fiscalTotals.ingresos)}</p></div>
                <div className="card"><p className="text-muted text-sm">Egresos año</p><p className="text-red-400 text-xl font-bold">{fmtMoney(fiscalTotals.egresos)}</p></div>
                <div className="card"><p className="text-muted text-sm">Neto</p><p className="text-xl font-bold">{fmtMoney(fiscalTotals.ingresos - fiscalTotals.egresos)}</p></div>
              </div>

              {monthKeys.map((key) => {
                const rows = months[key].slice().sort((a, b) => String(a.fecha_emision).localeCompare(String(b.fecha_emision)));
                const ingresos = rows.filter((r) => r.tipo === "E").reduce((sum, r) => sum + Number(r.total || 0), 0);
                const egresos = rows.filter((r) => r.tipo === "R").reduce((sum, r) => sum + Number(r.total || 0), 0);
                const monthIndex = Number(key.slice(5, 7)) - 1;
                return (
                  <details key={key} className="card" open={monthKeys.length <= 2}>
                    <summary className="cursor-pointer list-none">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div>
                          <p className="font-semibold">{MONTHS[monthIndex]} {key.slice(0, 4)}</p>
                          <p className="text-muted text-sm">{rows.length} CFDIs</p>
                        </div>
                        <div className="flex gap-4 text-sm">
                          <span className="text-green-400">Ingresos {fmtMoney(ingresos)}</span>
                          <span className="text-red-400">Egresos {fmtMoney(egresos)}</span>
                          <span>Neto {fmtMoney(ingresos - egresos)}</span>
                        </div>
                      </div>
                    </summary>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full text-sm">
                        <tbody>
                          {rows.map((row) => (
                            <tr key={String(row.uuid_cfdi)} className={clsx("border-b border-border/50", row.tipo === "E" ? "text-green-300" : "text-red-300")}>
                              <td className="py-2 pr-3 whitespace-nowrap text-slate-300">{asText(row.fecha_emision)}</td>
                              <td className="py-2 pr-3"><span className={tipoBadge(row.tipo)}>{tipoLabel(row.tipo)}</span></td>
                              <td className="py-2 pr-3 text-slate-300">{asText(row.rfc_emisor)} - {asText(row.nombre_emisor)}</td>
                              <td className="py-2 pr-3 text-slate-400">{asText(row.rfc_receptor)} - {asText(row.nombre_receptor)}</td>
                              <td className="py-2 text-right font-mono">{fmtMoney(row.total, String(row.moneda || "MXN"))}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
