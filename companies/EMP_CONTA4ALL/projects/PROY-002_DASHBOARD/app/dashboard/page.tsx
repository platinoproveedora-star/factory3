"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { COMPANY_CHANGE_EVENT, COMPANY_STORAGE_KEY, RFC_STORAGE_KEY } from "@/components/nav";
import OverviewChart from "./overview-chart";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type Cfdi = Record<string, JsonValue | undefined>;

interface Rfc { id: string; rfc: string; label?: string; company_id?: string | null; }
interface CompanyOption { company_id: string; name?: string; }

const MODULE_CODE = "conta4all";

const fmt = (n: number) => n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });

function uniqCount(rows: Cfdi[], key: string) {
  return new Set(rows.map((r) => String(r[key] || "").trim()).filter(Boolean)).size;
}

function avg(total: number, count: number) {
  return count ? total / count : 0;
}

function buildKpis(cfdis: Cfdi[]) {
  let ingresos = 0;
  let egresos = 0;
  let ivaIngresos = 0;
  let ivaEgresos = 0;
  let maxIngreso = 0;
  let maxEgreso = 0;
  let numIngresos = 0;
  let numEgresos = 0;
  const months = new Set<string>();

  for (const c of cfdis) {
    const total = Number(c.total || 0);
    const iva = Number(c.iva || 0);
    const month = String(c.fecha_emision || "").slice(0, 7);
    if (month) months.add(month);
    if (c.tipo === "E") {
      ingresos += total;
      ivaIngresos += iva;
      maxIngreso = Math.max(maxIngreso, total);
      numIngresos += 1;
    }
    if (c.tipo === "R") {
      egresos += total;
      ivaEgresos += iva;
      maxEgreso = Math.max(maxEgreso, total);
      numEgresos += 1;
    }
  }

  return {
    ingresos,
    egresos,
    neto: ingresos - egresos,
    ivaNeto: ivaIngresos - ivaEgresos,
    numCfdis: cfdis.length,
    numIngresos,
    numEgresos,
    avgIngreso: avg(ingresos, numIngresos),
    avgEgreso: avg(egresos, numEgresos),
    maxIngreso,
    maxEgreso,
    clientes: uniqCount(cfdis.filter((c) => c.tipo === "E"), "rfc_receptor"),
    proveedores: uniqCount(cfdis.filter((c) => c.tipo === "R"), "rfc_emisor"),
    meses: months.size,
  };
}

export default function DashboardPage() {
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [selectedRfc, setSelectedRfc] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [cfdis, setCfdis] = useState<Cfdi[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedCompany = companies.find((company) => company.company_id === selectedCompanyId);

  useEffect(() => {
    fetch("/api/auth/grants/me")
      .then((res) => res.json())
      .then((json) => {
        const grants = Array.isArray(json.grants) ? json.grants : [];
        const allowedCompanyIds = new Set(
          grants
            .filter((grant: any) => grant.modulo_code === MODULE_CODE)
            .map((grant: any) => String(grant.company_id || ""))
            .filter(Boolean)
        );
        const rows = (Array.isArray(json.companies) ? json.companies : []).filter((company: CompanyOption) =>
          allowedCompanyIds.has(company.company_id)
        );
        const stored = window.localStorage.getItem(COMPANY_STORAGE_KEY) || "";
        const initialCompany =
          rows.find((company: CompanyOption) => company.company_id === stored)?.company_id ||
          rows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
          rows[0]?.company_id ||
          "";
        setCompanies(rows);
        setSelectedCompanyId(initialCompany);
      })
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!selectedCompanyId) return;
    window.localStorage.setItem(COMPANY_STORAGE_KEY, selectedCompanyId);
    window.dispatchEvent(new CustomEvent(COMPANY_CHANGE_EVENT, { detail: selectedCompanyId }));
    setRfcs([]);
    setSelectedRfc("");
    setCfdis([]);
    setError("");
    fetch(`/api/rfcs?company_id=${encodeURIComponent(selectedCompanyId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          const rows = d.data?.rfcs ?? [];
          const storedRfc = window.localStorage.getItem(RFC_STORAGE_KEY) || "";
          setRfcs(rows);
          setSelectedRfc(rows.find((r: Rfc) => r.id === storedRfc)?.id || rows[0]?.id || "");
        } else {
          setError(d.error || "No se pudieron cargar RFCs");
        }
      })
      .catch(() => setError("No se pudieron cargar RFCs"));
  }, [selectedCompanyId]);

  useEffect(() => {
    if (selectedRfc) window.localStorage.setItem(RFC_STORAGE_KEY, selectedRfc);
  }, [selectedRfc]);

  const load = useCallback(async () => {
    if (!selectedRfc) return;
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({
        managed_rfc_id: selectedRfc,
        fecha_inicio: `${year}-01-01`,
        fecha_fin: `${year}-12-31`,
        limit: "10000",
      });
      const res = await fetch(`/api/cfdis?${qs}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Error consultando CFDIs");
      setCfdis(data.data?.cfdis ?? []);
    } catch (err) {
      setCfdis([]);
      setError(err instanceof Error ? err.message : "Error consultando CFDIs");
    } finally {
      setLoading(false);
    }
  }, [selectedRfc, year]);

  useEffect(() => {
    load();
  }, [load]);

  const kpis = useMemo(() => buildKpis(cfdis), [cfdis]);

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Resumen</h1>
      <p className="text-muted text-sm mb-6">Vista fiscal por RFC</p>

      <div className="card mb-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Empresa activa</p>
            <p className="mt-1 text-sm text-slate-300">
              {selectedCompany?.name || selectedCompanyId || "Selecciona una empresa"} · Los RFCs y el resumen se cargan para esta empresa.
            </p>
          </div>
          <select
            className="input md:max-w-sm"
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            disabled={!companies.length}
          >
            {companies.length === 0 ? <option value="">Sin empresas disponibles</option> : null}
            {companies.map((company) => (
              <option key={company.company_id} value={company.company_id}>
                {company.name || company.company_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!selectedCompanyId ? (
        <div className="card text-center py-12">
          <p className="text-muted">No tienes empresas activas para Conta4All.</p>
        </div>
      ) : rfcs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-muted mb-3">Esta empresa aun no tiene RFCs registrados</p>
          <Link href="/dashboard/rfcs" className="btn-primary">Agregar RFC</Link>
        </div>
      ) : (
        <>
          <div className="card mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="label">RFC</label>
                <select className="input" value={selectedRfc} onChange={(e) => setSelectedRfc(e.target.value)}>
                  {rfcs.map((r) => <option key={r.id} value={r.id}>{r.rfc}{r.label ? ` - ${r.label}` : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Ano</label>
                <input className="input" inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value)} />
              </div>
            </div>
          </div>

          {loading && <p className="text-muted text-sm mb-4">Cargando...</p>}
          {error && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm mb-4">{error}</div>}

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <div className="card"><p className="text-muted text-sm">Ingresos</p><p className="text-2xl font-bold text-green-400 mt-1">{fmt(kpis.ingresos)}</p></div>
            <div className="card"><p className="text-muted text-sm">Egresos</p><p className="text-2xl font-bold text-red-400 mt-1">{fmt(kpis.egresos)}</p></div>
            <div className="card"><p className="text-muted text-sm">Neto</p><p className="text-2xl font-bold mt-1">{fmt(kpis.neto)}</p></div>
            <div className="card"><p className="text-muted text-sm">IVA neto</p><p className="text-2xl font-bold mt-1">{fmt(kpis.ivaNeto)}</p></div>
            <div className="card"><p className="text-muted text-sm">CFDIs</p><p className="text-2xl font-bold mt-1">{kpis.numCfdis}</p></div>
            <div className="card"><p className="text-muted text-sm">Ingresos / Egresos</p><p className="text-2xl font-bold mt-1">{kpis.numIngresos} / {kpis.numEgresos}</p></div>
            <div className="card"><p className="text-muted text-sm">Promedio ingreso</p><p className="text-2xl font-bold mt-1">{fmt(kpis.avgIngreso)}</p></div>
            <div className="card"><p className="text-muted text-sm">Promedio egreso</p><p className="text-2xl font-bold mt-1">{fmt(kpis.avgEgreso)}</p></div>
            <div className="card"><p className="text-muted text-sm">Ingreso mayor</p><p className="text-2xl font-bold mt-1">{fmt(kpis.maxIngreso)}</p></div>
            <div className="card"><p className="text-muted text-sm">Egreso mayor</p><p className="text-2xl font-bold mt-1">{fmt(kpis.maxEgreso)}</p></div>
            <div className="card"><p className="text-muted text-sm">Clientes / Proveedores</p><p className="text-2xl font-bold mt-1">{kpis.clientes} / {kpis.proveedores}</p></div>
            <div className="card"><p className="text-muted text-sm">Meses activos</p><p className="text-2xl font-bold mt-1">{kpis.meses}</p></div>
          </div>

          <div className="card mb-6">
            <OverviewChart cfdis={cfdis} />
          </div>
          <div className="flex gap-3">
            <Link href="/dashboard/sincronizar" className="btn-primary">Sincronizar SAT</Link>
            <Link href="/dashboard/cfdis" className="btn-ghost">Ver CFDIs</Link>
          </div>
        </>
      )}
    </div>
  );
}
