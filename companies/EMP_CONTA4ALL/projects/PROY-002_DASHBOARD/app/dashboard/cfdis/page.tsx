"use client";
import { useState, useEffect, useCallback } from "react";
import clsx from "clsx";

interface Cfdi {
  uuid_cfdi: string;
  tipo: string;
  fecha_emision: string;
  rfc_emisor: string;
  nombre_emisor: string;
  rfc_receptor: string;
  nombre_receptor: string;
  subtotal: number;
  total: number;
  moneda: string;
  tipo_comprobante: string;
}

interface Rfc { id: string; rfc: string; label?: string; }

const fmt = (n: number, m = "MXN") =>
  Number(n).toLocaleString("es-MX", { style: "currency", currency: m });

export default function CfdisPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [filters, setFilters] = useState({
    managed_rfc_id: "",
    tipo: "",
    fecha_inicio: "",
    fecha_fin: "",
  });
  const [cfdis, setCfdis] = useState<Cfdi[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    fetch("/api/rfcs").then((r) => r.json()).then((d) => {
      if (d.ok) setRfcs(d.data?.rfcs ?? []);
    });
  }, []);

  const handleSearch = useCallback(async () => {
    if (!filters.managed_rfc_id) return;
    setLoading(true); setSearched(true);
    const qs = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
    const res = await fetch(`/api/cfdis?${qs}`);
    const data = await res.json();
    setCfdis(data.ok ? data.data?.cfdis ?? [] : []);
    setLoading(false);
  }, [filters]);

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">CFDIs</h1>
      <p className="text-muted text-sm mb-6">Ingresos y egresos sincronizados del SAT</p>

      <div className="card mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="col-span-2 sm:col-span-1">
            <label className="label">RFC</label>
            <select className="input" value={filters.managed_rfc_id} onChange={(e) => setFilters((f) => ({ ...f, managed_rfc_id: e.target.value }))}>
              <option value="">Todos</option>
              {rfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Tipo</label>
            <select className="input" value={filters.tipo} onChange={(e) => setFilters((f) => ({ ...f, tipo: e.target.value }))}>
              <option value="">Todos</option>
              <option value="E">Ingresos (Emitidos)</option>
              <option value="R">Egresos (Recibidos)</option>
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
        <div className="mt-3">
          <button className="btn-primary" onClick={handleSearch} disabled={!filters.managed_rfc_id || loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </div>
      </div>

      {loading && <p className="text-muted text-sm">Cargando...</p>}

      {!loading && searched && cfdis.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-muted">No se encontraron CFDIs con esos filtros</p>
        </div>
      )}

      {!loading && cfdis.length > 0 && (
        <>
          <p className="text-muted text-sm mb-3">{cfdis.length} CFDIs encontrados</p>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead className="bg-card text-muted border-b border-border">
                <tr>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Tipo</th>
                  <th className="text-left px-4 py-3">Emisor</th>
                  <th className="text-left px-4 py-3">Contraparte</th>
                  <th className="text-right px-4 py-3">Total</th>
                </tr>
              </thead>
              <tbody>
                {cfdis.map((c) => (
                  <tr key={c.uuid_cfdi} className="border-b border-border/50 hover:bg-card/60 transition-colors">
                    <td className="px-4 py-3 text-muted">{c.fecha_emision}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(c.tipo === "E" ? "badge-green" : "badge-red")}>
                        {c.tipo === "E" ? "Ingreso" : "Egreso"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-mono text-xs">{c.rfc_emisor}</p>
                      <p className="text-muted text-xs truncate max-w-[160px]">{c.nombre_emisor}</p>
                    </td>
                    <td className="px-4 py-3 text-muted text-xs truncate max-w-[180px]">
                      {c.rfc_receptor} {c.nombre_receptor ? `- ${c.nombre_receptor}` : ""}
                    </td>
                    <td className={clsx("px-4 py-3 text-right font-mono font-medium", c.tipo === "E" ? "text-green-400" : "text-red-400")}>
                      {fmt(c.total, c.moneda)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
