"use client";

import { useState, useMemo } from "react";
import {
  Search, Download, ChevronLeft, ChevronRight,
  Plus, Trash2, Pencil, Check, X, ChevronUp, ChevronDown,
} from "lucide-react";
import type { BankAccount, Gasto } from "@/lib/db";
import { SCHEMA } from "@/lib/constants";

type Props = { gastos: Gasto[]; bankAccounts: BankAccount[]; empresaId: string; projectCode?: string };
type EditDraft = { monto: string; fecha: string; descripcion: string; categoria: string; vehiculo: string; cta_retiro_id: string };

const PAGE_SIZE = 50;
const READ_SKILL  = "vertical_client_expenses/client_expenses_dashboard_data";
const WRITE_SKILL = "vertical_client_expenses/client_expenses_run";

const METHOD_LABEL: Record<string, string> = {
  foto: "📷", manual: "⌨️", api: "🔌", ai_ocr: "🤖", import_excel: "📊", dashboard: "🖥️",
};

function mxn(n: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 2 }).format(n);
}

function fmtDate(s: string) {
  if (!s) return "—";
  const [y, m, d] = s.split("-");
  const months = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  return `${d} ${months[Number(m) - 1]} ${y}`;
}

function gastosToCSV(rows: Gasto[]) {
  const h = ["folio","fecha","categoria","vehiculo","cta_retiro","descripcion","usuario","metodo","monto"];
  const b = rows.map((g) =>
    [g.folio,g.fecha,g.categoria,g.vehiculo||"",g.cta_retiro_nombre||"",g.descripcion,g.nombre_usuario,g.metodo_captura,g.monto]
      .map((v) => `"${String(v??"").replace(/"/g,'""')}"`)
      .join(",")
  );
  return [h.join(","), ...b].join("\n");
}

export default function ExpenseTable({ gastos: initialGastos, bankAccounts, empresaId, projectCode = "GASTOS4ALL_V1" }: Props) {
  const [gastos, setGastos]         = useState<Gasto[]>(initialGastos);
  const [q, setQ]                   = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [page, setPage]             = useState(0);
  const [sortCol, setSortCol]       = useState<keyof Gasto>("fecha");
  const [sortDir, setSortDir]       = useState<"asc"|"desc">("desc");
  const [editingFolio, setEdit]     = useState<string | null>(null);
  const [draft, setDraft]           = useState<EditDraft>({ monto:"", fecha:"", descripcion:"", categoria:"", vehiculo:"", cta_retiro_id:"" });
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");
  const [adding, setAdding]         = useState(false);
  const [newRow, setNewRow]         = useState<EditDraft>({ monto:"", fecha: new Date().toISOString().slice(0,10), descripcion:"", categoria:"", vehiculo:"", cta_retiro_id:"" });

  const CATEGORIES = useMemo(() => {
    const from = Array.from(new Set(gastos.map((g) => g.categoria).filter(Boolean))).sort();
    return from.length > 0 ? from : ["combustible","gastos varios","taller","nomina","otros"];
  }, [gastos]);

  const accountById = useMemo(() => new Map(bankAccounts.map((a) => [a.id, a])), [bankAccounts]);

  const baseCtx = {
    schema: SCHEMA,
    empresa_id: empresaId,
    company_id: empresaId,
    project_code: projectCode,
    module_code: "gastos4all",
    dry_run: false,
  };

  const factoryUrl = process.env.NEXT_PUBLIC_FACTORY_API_URL ?? "";

  async function skillPost(skill: string, action: string, extra: object) {
    const res = await fetch(`${factoryUrl}/data/${skill}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...baseCtx, action, ...extra }),
    });
    const json = await res.json();
    if (!res.ok || json?.ok === false) throw new Error(json?.error ?? "Error en skill");
    return json?.data ?? json;
  }

  const filtered = useMemo(() => {
    const lq = q.toLowerCase().trim();
    return gastos
      .filter((g) => {
        if (lq && !`${g.descripcion} ${g.categoria} ${g.nombre_usuario} ${g.folio}`.toLowerCase().includes(lq)) return false;
        if (fechaDesde && g.fecha < fechaDesde) return false;
        if (fechaHasta && g.fecha > fechaHasta) return false;
        return true;
      })
      .sort((a, b) => {
        const av = a[sortCol] ?? ""; const bv = b[sortCol] ?? "";
        const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      });
  }, [gastos, q, fechaDesde, fechaHasta, sortCol, sortDir]);

  function toggleSort(col: keyof Gasto) {
    if (sortCol === col) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("desc"); }
    setPage(0);
  }

  function SortIcon({ col }: { col: keyof Gasto }) {
    if (sortCol !== col) return <ChevronUp size={11} className="opacity-20" />;
    return sortDir === "asc" ? <ChevronUp size={11} /> : <ChevronDown size={11} />;
  }

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const slice      = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function startEdit(g: Gasto) {
    setEdit(g.folio);
    setDraft({ monto: String(g.monto), fecha: g.fecha, descripcion: g.descripcion, categoria: g.categoria, vehiculo: g.vehiculo ?? "", cta_retiro_id: g.cta_retiro_id ?? "" });
    setError("");
  }

  async function saveEdit(folio: string) {
    setSaving(true); setError("");
    try {
      await skillPost(WRITE_SKILL, "update_expense", {
        folio,
        monto: parseFloat(draft.monto),
        fecha: draft.fecha,
        descripcion: draft.descripcion,
        categoria: draft.categoria,
        vehiculo: draft.vehiculo || null,
        cta_retiro_id: draft.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(draft.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(draft.cta_retiro_id)?.account_name || null,
      });
      setGastos((prev) =>
        prev.map((g) =>
          g.folio === folio
            ? { ...g, monto: parseFloat(draft.monto), fecha: draft.fecha, descripcion: draft.descripcion, categoria: draft.categoria, vehiculo: draft.vehiculo || null, cta_retiro_id: draft.cta_retiro_id || null, cta_retiro_nombre: accountById.get(draft.cta_retiro_id)?.account_name || null, cta_retiro_folio: accountById.get(draft.cta_retiro_id)?.folio || null }
            : g
        )
      );
      setEdit(null);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  }

  async function deleteRow(folio: string) {
    if (!confirm(`¿Eliminar ${folio}?`)) return;
    setSaving(true); setError("");
    try {
      await skillPost(WRITE_SKILL, "delete_expense", { folio });
      setGastos((prev) => prev.filter((g) => g.folio !== folio));
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  }

  async function addExpense() {
    if (!newRow.monto || !newRow.fecha || !newRow.categoria) {
      setError("Monto, fecha y categoría requeridos"); return;
    }
    setSaving(true); setError("");
    try {
      const userRes = await skillPost(WRITE_SKILL, "register_user", { nombre: "dashboard", telegram_chat_id: "dashboard" });
      const usuario_id = userRes?.user?.id ?? userRes?.data?.user?.id ?? "";
      const result = await skillPost(WRITE_SKILL, "save_expense", {
        usuario_id,
        monto: parseFloat(newRow.monto),
        fecha: newRow.fecha,
        descripcion: newRow.descripcion,
        categoria: newRow.categoria,
        vehiculo: newRow.vehiculo || null,
        cta_retiro_id: newRow.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(newRow.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(newRow.cta_retiro_id)?.account_name || null,
        metodo_captura: "dashboard",
      });
      const saved = result?.gasto ?? {};
      setGastos((prev) => [{
        folio: saved.folio ?? "—", fecha: newRow.fecha,
        monto: parseFloat(newRow.monto), descripcion: newRow.descripcion,
        metodo_captura: "dashboard", categoria: newRow.categoria,
        vehiculo: newRow.vehiculo || null,
        cta_retiro_id: newRow.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(newRow.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(newRow.cta_retiro_id)?.account_name || null,
        nombre_usuario: "dashboard",
      }, ...prev]);
      setNewRow({ monto:"", fecha: new Date().toISOString().slice(0,10), descripcion:"", categoria: CATEGORIES[0] ?? "", vehiculo:"", cta_retiro_id:"" });
      setAdding(false);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  }

  function handleExport() {
    const blob = new Blob([gastosToCSV(filtered)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `gastos4all-${new Date().toISOString().slice(0,10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  const inputCls = "rounded border border-border bg-slate-800 px-2 py-1 text-xs text-slate-100 focus:border-primary focus:outline-none";
  const selectCls = "rounded border border-border bg-slate-800 px-2 py-1 text-xs text-slate-100 focus:border-primary focus:outline-none";

  return (
    <div>
      {/* Toolbar */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[180px] flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input type="text" placeholder="Buscar descripción, categoría, folio…" value={q}
            onChange={(e) => { setQ(e.target.value); setPage(0); }}
            className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm text-slate-100 placeholder-muted outline-none focus:border-primary" />
        </div>
        <input type="date" value={fechaDesde} title="Desde"
          onChange={(e) => { setFechaDesde(e.target.value); setPage(0); }}
          className="rounded-lg border border-border bg-card px-2 py-2 text-sm text-slate-300 outline-none focus:border-primary" />
        <input type="date" value={fechaHasta} title="Hasta"
          onChange={(e) => { setFechaHasta(e.target.value); setPage(0); }}
          className="rounded-lg border border-border bg-card px-2 py-2 text-sm text-slate-300 outline-none focus:border-primary" />
        {(fechaDesde || fechaHasta) && (
          <button onClick={() => { setFechaDesde(""); setFechaHasta(""); setPage(0); }} className="text-xs text-muted hover:text-white">✕</button>
        )}
        <span className="whitespace-nowrap text-xs text-muted">{filtered.length} resultados</span>
        <button onClick={() => { setAdding(true); setError(""); }} className="btn-primary inline-flex items-center gap-1.5">
          <Plus size={14} /> Nuevo gasto
        </button>
        <button onClick={handleExport} className="btn-ghost inline-flex items-center gap-2">
          <Download size={14} /> CSV
        </button>
      </div>

      {error && <div className="mb-3 rounded-lg border border-red-800 bg-red-900/30 px-4 py-2 text-xs text-red-400">{error}</div>}

      {/* New expense form */}
      {adding && (
        <div className="mb-4 rounded-xl border border-primary/40 bg-primary/5 p-4">
          <p className="mb-3 text-xs font-semibold text-primary">Nuevo gasto</p>
          <div className="flex flex-wrap items-end gap-2">
            <div><label className="label">Monto</label><input type="number" placeholder="0.00" value={newRow.monto} onChange={(e) => setNewRow((p) => ({...p, monto: e.target.value}))} className={inputCls + " w-28"} /></div>
            <div><label className="label">Fecha</label><input type="date" value={newRow.fecha} onChange={(e) => setNewRow((p) => ({...p, fecha: e.target.value}))} className={inputCls} /></div>
            <div><label className="label">Categoría</label>
              <select value={newRow.categoria} onChange={(e) => setNewRow((p) => ({...p, categoria: e.target.value}))} className={selectCls}>
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div><label className="label">Vehículo</label><input type="text" placeholder="ej: Torton 01" value={newRow.vehiculo} onChange={(e) => setNewRow((p) => ({...p, vehiculo: e.target.value}))} className={inputCls + " w-28"} /></div>
            <div><label className="label">Cta retiro</label>
              <select value={newRow.cta_retiro_id} onChange={(e) => setNewRow((p) => ({...p, cta_retiro_id: e.target.value}))} className={selectCls + " min-w-[160px]"}>
                <option value="">Sin asignar</option>
                {bankAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
              </select>
            </div>
            <div className="min-w-[160px] flex-1"><label className="label">Descripción</label><input type="text" placeholder="opcional" value={newRow.descripcion} onChange={(e) => setNewRow((p) => ({...p, descripcion: e.target.value}))} className={inputCls + " w-full"} /></div>
            <button onClick={addExpense} disabled={saving} className="btn-primary inline-flex items-center gap-1"><Check size={14} /> Guardar</button>
            <button onClick={() => { setAdding(false); setError(""); }} className="btn-ghost inline-flex items-center gap-1"><X size={14} /> Cancelar</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="table-head">
            <tr>
              {([ ["Folio","folio"],["Fecha","fecha"],["Categoría","categoria"],["Vehículo","vehiculo"],["Cta retiro","cta_retiro_nombre"],["Descripción","descripcion"],["Usuario","nombre_usuario"],["Método","metodo_captura"],["Monto","monto"],["",""] ] as [string,string][]).map(([label, col]) => (
                <th key={label} onClick={() => col && toggleSort(col as keyof Gasto)} className={`px-3 py-3 ${col ? "cursor-pointer select-none hover:text-slate-300" : ""}`}>
                  <span className="inline-flex items-center gap-1">{label}{col && <SortIcon col={col as keyof Gasto} />}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50 bg-card">
            {slice.length === 0 ? (
              <tr><td colSpan={10} className="py-10 text-center text-sm text-muted">Sin resultados</td></tr>
            ) : slice.map((g) => {
              const isEditing = editingFolio === g.folio;
              return (
                <tr key={g.folio} className={isEditing ? "bg-primary/10" : "group hover:bg-slate-700/30"}>
                  <td className="px-3 py-2 font-mono text-xs text-muted">{g.folio}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {isEditing ? <input type="date" value={draft.fecha} onChange={(e) => setDraft((p) => ({...p, fecha: e.target.value}))} className={inputCls + " w-32"} /> : fmtDate(g.fecha)}
                  </td>
                  <td className="px-3 py-2">
                    {isEditing ? <select value={draft.categoria} onChange={(e) => setDraft((p) => ({...p, categoria: e.target.value}))} className={selectCls}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select>
                      : <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs font-medium text-slate-200">{g.categoria || "—"}</span>}
                  </td>
                  <td className="px-3 py-2">
                    {isEditing ? <input type="text" value={draft.vehiculo} onChange={(e) => setDraft((p) => ({...p, vehiculo: e.target.value}))} className={inputCls + " w-24"} />
                      : <span className="text-xs text-slate-400">{g.vehiculo || "—"}</span>}
                  </td>
                  <td className="px-3 py-2">
                    {isEditing ? <select value={draft.cta_retiro_id} onChange={(e) => setDraft((p) => ({...p, cta_retiro_id: e.target.value}))} className={selectCls + " min-w-[140px]"}><option value="">Sin asignar</option>{bankAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}</select>
                      : <span className="text-xs text-slate-400">{g.cta_retiro_nombre || "Sin asignar"}</span>}
                  </td>
                  <td className="max-w-[200px] px-3 py-2">
                    {isEditing ? <input type="text" value={draft.descripcion} onChange={(e) => setDraft((p) => ({...p, descripcion: e.target.value}))} className={inputCls + " w-full"} />
                      : <span className="block truncate" title={g.descripcion}>{g.descripcion || "—"}</span>}
                  </td>
                  <td className="px-3 py-2 text-slate-400">{g.nombre_usuario || "—"}</td>
                  <td className="px-3 py-2 text-xs text-muted">{METHOD_LABEL[g.metodo_captura] ?? g.metodo_captura}</td>
                  <td className="px-3 py-2 text-right font-semibold text-white">
                    {isEditing ? <input type="number" min="0" value={draft.monto} onChange={(e) => setDraft((p) => ({...p, monto: e.target.value}))} className={inputCls + " w-24 text-right"} /> : mxn(g.monto)}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {isEditing ? (
                      <div className="flex gap-1">
                        <button onClick={() => saveEdit(g.folio)} disabled={saving} className="rounded bg-emerald-900/50 p-1 text-emerald-400 hover:bg-emerald-900 disabled:opacity-40"><Check size={13} /></button>
                        <button onClick={() => setEdit(null)} className="rounded bg-slate-700 p-1 text-slate-300 hover:bg-slate-600"><X size={13} /></button>
                      </div>
                    ) : (
                      <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button onClick={() => startEdit(g)} className="rounded p-1 text-muted hover:bg-slate-700 hover:text-white"><Pencil size={13} /></button>
                        <button onClick={() => deleteRow(g.folio)} disabled={saving} className="rounded p-1 text-muted hover:bg-red-900/50 hover:text-red-400 disabled:opacity-40"><Trash2 size={13} /></button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between text-sm text-muted">
          <span>Pág {safePage + 1} de {totalPages}</span>
          <div className="flex gap-2">
            <button disabled={safePage === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} className="rounded border border-border p-1 disabled:opacity-40 hover:bg-card"><ChevronLeft size={16} /></button>
            <button disabled={safePage >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} className="rounded border border-border p-1 disabled:opacity-40 hover:bg-card"><ChevronRight size={16} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
