"use client";
import { useState, useEffect, useCallback } from "react";
import clsx from "clsx";
import { COMPANY_CHANGE_EVENT, COMPANY_STORAGE_KEY } from "@/components/nav";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type Cfdi = Record<string, JsonValue | undefined>;
type Totals = {
  ingresos: number;
  egresos: number;
  ivaIngresos: number;
  ivaEgresos: number;
  numIngresos: number;
  numEgresos: number;
};

interface Rfc { id: string; rfc: string; label?: string; company_id?: string | null; }

const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const COLUMN_LABELS: Record<string, string> = {
  fecha_emision: "Fecha",
  tipo: "Movimiento",
  rfc_emisor: "RFC emisor",
  nombre_emisor: "Emisor",
  rfc_receptor: "RFC receptor",
  nombre_receptor: "Receptor",
  conceptos: "Conceptos",
  iva: "IVA",
  total: "Total",
  moneda: "Moneda",
  tipo_comprobante: "Tipo",
  metodo_pago: "Metodo pago",
  forma_pago: "Forma pago",
  uso_cfdi: "Uso CFDI",
  fecha_timbrado: "Timbrado",
};

const HIDDEN_COLUMNS = new Set([
  "uuid_cfdi", "id", "subtotal", "descuento", "xml_raw", "has_xml",
  "pdf_url", "impuestos",
]);

const PREFERRED_COLUMNS = [
  "fecha_emision", "tipo", "tipo_comprobante", "rfc_emisor", "nombre_emisor",
  "rfc_receptor", "nombre_receptor", "conceptos", "iva", "total",
  "moneda", "metodo_pago", "forma_pago", "uso_cfdi", "fecha_timbrado",
];

const fmtMoney = (n: unknown, m = "MXN") =>
  Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: m || "MXN" });

const asText = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "-";
  if (Array.isArray(value)) return value.length ? JSON.stringify(value) : "-";
  if (typeof value === "object") return Object.keys(value).length ? JSON.stringify(value) : "-";
  return String(value);
};

const movementLabel = (tipo: unknown) => String(tipo) === "E" ? "Ingreso" : "Egreso";
const movementBadge = (tipo: unknown) => String(tipo) === "E" ? "badge-green" : "badge-red";

function getConceptos(row: Cfdi) {
  const conceptos = row.conceptos;
  if (Array.isArray(conceptos)) {
    const parts = conceptos
      .map((c) => typeof c === "object" && c ? String((c as Record<string, JsonValue>).descripcion || "") : String(c || ""))
      .filter(Boolean);
    return parts.join("; ") || "-";
  }
  return asText(conceptos);
}

function sortedColumns(rows: Cfdi[]) {
  const found = new Set(rows.flatMap((row) => Object.keys(row)).filter((key) => !HIDDEN_COLUMNS.has(key)));
  return [
    ...PREFERRED_COLUMNS.filter((key) => found.has(key)),
    ...Array.from(found).filter((key) => !PREFERRED_COLUMNS.includes(key)).sort(),
    "acciones",
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

function calcTotals(rows: Cfdi[]) {
  return rows.reduce<Totals>(
    (acc, row) => {
      const total = Number(row.total || 0);
      const iva = Number(row.iva || 0);
      if (row.tipo === "E") {
        acc.ingresos += total;
        acc.ivaIngresos += iva;
        acc.numIngresos += 1;
      }
      if (row.tipo === "R") {
        acc.egresos += total;
        acc.ivaEgresos += iva;
        acc.numEgresos += 1;
      }
      return acc;
    },
    { ingresos: 0, egresos: 0, ivaIngresos: 0, ivaEgresos: 0, numIngresos: 0, numEgresos: 0 }
  );
}

function renderCell(row: Cfdi, col: string) {
  if (col === "tipo") return <span className={movementBadge(row.tipo)}>{movementLabel(row.tipo)}</span>;
  if (col === "conceptos") return <span className="block max-w-[420px] truncate" title={getConceptos(row)}>{getConceptos(row)}</span>;
  if (col === "total" || col === "iva") return fmtMoney(row[col], String(row.moneda || "MXN"));
  return asText(row[col]);
}

function DocActions({ row, managedRfcId }: { row: Cfdi; managedRfcId: string }) {
  const uuid = String(row.uuid_cfdi || "");
  const pdfUrl = String(row.pdf_url || "");
  const hasXml = Boolean(row.has_xml || row.xml_raw);

  const fetchXml = async () => {
    const qs = new URLSearchParams({ managed_rfc_id: managedRfcId, uuid_cfdi: uuid, include_xml: "1", limit: "1" });
    const res = await fetch(`/api/cfdis?${qs}`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "No se pudo abrir XML");
    const xml = data.data?.cfdis?.[0]?.xml_raw || "";
    if (!xml) throw new Error("Este CFDI no tiene XML guardado");
    return String(xml);
  };

  const downloadXml = async () => {
    try {
      const xml = await fetchXml();
      const blob = new Blob([xml], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${uuid || "cfdi"}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "No se pudo descargar XML");
    }
  };

  const printXml = async () => {
    try {
      const xml = await fetchXml();
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(`<pre style="white-space:pre-wrap;font:12px ui-monospace,monospace">${xml.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch] || ch))}</pre>`);
      w.document.close();
      w.print();
    } catch (err) {
      alert(err instanceof Error ? err.message : "No se pudo imprimir XML");
    }
  };

  return (
    <div className="flex gap-1 justify-end">
      <button className="border border-border rounded px-1.5 py-1 text-[10px] hover:border-slate-400 disabled:opacity-30" onClick={printXml} disabled={!hasXml} title="Imprimir XML">
        P
      </button>
      <button className="border border-border rounded px-1.5 py-1 text-[10px] hover:border-slate-400 disabled:opacity-30" onClick={downloadXml} disabled={!hasXml} title="Descargar XML">
        XML
      </button>
      {pdfUrl ? (
        <a className="border border-border rounded px-1.5 py-1 text-[10px] hover:border-slate-400" href={pdfUrl} target="_blank" rel="noreferrer" title="Abrir PDF">
          PDF
        </a>
      ) : (
        <button className="border border-border rounded px-1.5 py-1 text-[10px] opacity-30" disabled title="PDF no guardado">
          PDF
        </button>
      )}
    </div>
  );
}

export default function CfdisPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [activeTab, setActiveTab] = useState<"buscar" | "fiscal">("buscar");
  const [filters, setFilters] = useState({ managed_rfc_id: "", tipo: "", fecha_inicio: "", fecha_fin: "" });
  const [fiscal, setFiscal] = useState({ managed_rfc_id: "", year: String(new Date().getFullYear()) });
  const [cfdis, setCfdis] = useState<Cfdi[]>([]);
  const [fiscalCfdis, setFiscalCfdis] = useState<Cfdi[]>([]);
  const [loading, setLoading] = useState(false);
  const [fiscalLoading, setFiscalLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [fiscalSearched, setFiscalSearched] = useState(false);
  const [error, setError] = useState("");
  const [fiscalError, setFiscalError] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState("");

  useEffect(() => {
    fetch("/api/rfcs").then((r) => r.json()).then((d) => {
      if (d.ok) {
        const rows = d.data?.rfcs ?? [];
        setRfcs(rows);
      }
    });
  }, []);

  useEffect(() => {
    setSelectedCompanyId(window.localStorage.getItem(COMPANY_STORAGE_KEY) || "");
    const onCompanyChange = (event: Event) => {
      setSelectedCompanyId(String((event as CustomEvent).detail || ""));
    };
    window.addEventListener(COMPANY_CHANGE_EVENT, onCompanyChange);
    return () => window.removeEventListener(COMPANY_CHANGE_EVENT, onCompanyChange);
  }, []);

  const companyRfcs = selectedCompanyId
    ? rfcs.filter((r) => r.company_id === selectedCompanyId)
    : [];
  const visibleRfcs = companyRfcs.length ? companyRfcs : rfcs;

  useEffect(() => {
    if (visibleRfcs.length !== 1) return;
    const onlyId = visibleRfcs[0].id;
    setFilters((f) => (f.managed_rfc_id === onlyId ? f : { ...f, managed_rfc_id: onlyId }));
    setFiscal((f) => (f.managed_rfc_id === onlyId ? f : { ...f, managed_rfc_id: onlyId }));
  }, [visibleRfcs]);

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
  const fiscalTotals = calcTotals(fiscalCfdis);

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">CFDIs</h1>
      <p className="text-muted text-sm mb-6">Ingresos y egresos sincronizados del SAT</p>

      <div className="flex gap-2 mb-5">
        <button className={activeTab === "buscar" ? "btn-primary" : "btn-ghost"} onClick={() => setActiveTab("buscar")}>Buscador</button>
        <button className={activeTab === "fiscal" ? "btn-primary" : "btn-ghost"} onClick={() => setActiveTab("fiscal")}>Ano fiscal</button>
      </div>

      {activeTab === "buscar" && (
        <>
          <div className="card mb-6">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="col-span-2 sm:col-span-1">
                <label className="label">RFC</label>
                <select className="input" value={filters.managed_rfc_id} onChange={(e) => setFilters((f) => ({ ...f, managed_rfc_id: e.target.value }))}>
                  <option value="">Selecciona RFC</option>
                  {visibleRfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}{r.label ? ` - ${r.label}` : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Movimiento</label>
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
                        <th key={col} className={clsx("px-3 py-3 whitespace-nowrap", col === "total" || col === "iva" || col === "acciones" ? "text-right" : "text-left")}>
                          {col === "acciones" ? "" : COLUMN_LABELS[col] ?? col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cfdis.map((row, idx) => (
                      <tr key={`${String(row.uuid_cfdi || idx)}`} className="border-b border-border/50 hover:bg-card/60 transition-colors">
                        {columns.map((col) => (
                          <td key={col} className={clsx("px-3 py-2 align-top", col === "total" || col === "iva" ? "text-right font-mono whitespace-nowrap" : "whitespace-nowrap")}>
                            {col === "acciones" ? <DocActions row={row} managedRfcId={filters.managed_rfc_id} /> : renderCell(row, col)}
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
                  {visibleRfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}{r.label ? ` - ${r.label}` : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Ano</label>
                <input className="input" inputMode="numeric" value={fiscal.year} onChange={(e) => setFiscal((f) => ({ ...f, year: e.target.value }))} />
              </div>
              <div className="flex items-end">
                <button className="btn-primary w-full" onClick={handleFiscalSearch} disabled={!fiscal.managed_rfc_id || !fiscal.year || fiscalLoading}>
                  {fiscalLoading ? "Buscando..." : "Buscar ano fiscal"}
                </button>
              </div>
            </div>
          </div>

          {fiscalLoading && <p className="text-muted text-sm">Cargando...</p>}
          {!fiscalLoading && fiscalError && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm">{fiscalError}</div>}
          {!fiscalLoading && fiscalSearched && !fiscalError && fiscalCfdis.length === 0 && (
            <div className="card text-center py-12"><p className="text-muted">No hay CFDIs para ese ano</p></div>
          )}

          {!fiscalLoading && fiscalCfdis.length > 0 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div className="card"><p className="text-muted text-sm">Ingresos ano</p><p className="text-green-400 text-xl font-bold">{fmtMoney(fiscalTotals.ingresos)}</p></div>
                <div className="card"><p className="text-muted text-sm">Egresos ano</p><p className="text-red-400 text-xl font-bold">{fmtMoney(fiscalTotals.egresos)}</p></div>
                <div className="card"><p className="text-muted text-sm">IVA neto</p><p className="text-xl font-bold">{fmtMoney(fiscalTotals.ivaIngresos - fiscalTotals.ivaEgresos)}</p></div>
                <div className="card"><p className="text-muted text-sm">Neto</p><p className="text-xl font-bold">{fmtMoney(fiscalTotals.ingresos - fiscalTotals.egresos)}</p></div>
              </div>

              {monthKeys.map((key) => {
                const rows = months[key].slice().sort((a, b) => String(a.fecha_emision).localeCompare(String(b.fecha_emision)));
                const totals = calcTotals(rows);
                const monthIndex = Number(key.slice(5, 7)) - 1;
                return (
                  <details key={key} className="card" open={monthKeys.length <= 2}>
                    <summary className="cursor-pointer list-none">
                      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2">
                        <div>
                          <p className="font-semibold">{MONTHS[monthIndex]} {key.slice(0, 4)}</p>
                          <p className="text-muted text-sm">{rows.length} CFDIs</p>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                          <span className="text-green-400">Ingresos {fmtMoney(totals.ingresos)}</span>
                          <span className="text-red-400">Egresos {fmtMoney(totals.egresos)}</span>
                          <span>IVA {fmtMoney(totals.ivaIngresos - totals.ivaEgresos)}</span>
                          <span>Neto {fmtMoney(totals.ingresos - totals.egresos)}</span>
                        </div>
                      </div>
                    </summary>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full text-sm">
                        <tbody>
                          {rows.map((row, idx) => (
                            <tr key={`${String(row.uuid_cfdi || idx)}`} className={clsx("border-b border-border/50", row.tipo === "E" ? "text-green-300" : "text-red-300")}>
                              <td className="py-2 pr-3 whitespace-nowrap text-slate-300">{asText(row.fecha_emision)}</td>
                              <td className="py-2 pr-3"><span className={movementBadge(row.tipo)}>{movementLabel(row.tipo)}</span></td>
                              <td className="py-2 pr-3 text-slate-300">{asText(row.nombre_emisor || row.rfc_emisor)}</td>
                              <td className="py-2 pr-3 text-slate-400 max-w-[360px] truncate" title={getConceptos(row)}>{getConceptos(row)}</td>
                              <td className="py-2 pr-3 text-right font-mono whitespace-nowrap">{fmtMoney(row.iva, String(row.moneda || "MXN"))}</td>
                              <td className="py-2 pr-3 text-right font-mono whitespace-nowrap">{fmtMoney(row.total, String(row.moneda || "MXN"))}</td>
                              <td className="py-2"><DocActions row={row} managedRfcId={fiscal.managed_rfc_id} /></td>
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
