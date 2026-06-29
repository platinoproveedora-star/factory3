"use client";

import { useMemo, useState } from "react";
import { Check, Download, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import type { BankAccount, Gasto } from "@/lib/gastos";

type Stats = {
  total: number;
  count: number;
  avg: number;
  por_categoria: Array<{ categoria: string; total: number; count: number }>;
};

type Draft = {
  folio?: string;
  monto: string;
  fecha: string;
  categoria: string;
  vehiculo: string;
  descripcion: string;
  cta_retiro_id: string;
};

function mxn(value: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value || 0);
}

function csv(rows: Gasto[]) {
  const headers = ["folio", "fecha", "categoria", "vehiculo", "cta_retiro", "descripcion", "usuario", "metodo", "monto"];
  const body = rows.map((row) =>
    [row.folio, row.fecha, row.categoria, row.vehiculo || "", row.cta_retiro_nombre || "", row.descripcion, row.nombre_usuario, row.metodo_captura, row.monto]
      .map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`)
      .join(",")
  );
  return [headers.join(","), ...body].join("\n");
}

export function GastosDashboard({
  initialGastos,
  initialStats,
  categories,
  bankAccounts
}: {
  initialGastos: Gasto[];
  initialStats: Stats;
  categories: string[];
  bankAccounts: BankAccount[];
}) {
  const [gastos, setGastos] = useState(initialGastos);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Draft>({
    monto: "",
    fecha: new Date().toISOString().slice(0, 10),
    categoria: categories[0] || "combustible",
    vehiculo: "",
    descripcion: "",
    cta_retiro_id: ""
  });

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return gastos;
    return gastos.filter((row) =>
      `${row.folio} ${row.fecha} ${row.categoria} ${row.descripcion} ${row.vehiculo || ""} ${row.cta_retiro_nombre || ""}`
        .toLowerCase()
        .includes(term)
    );
  }, [gastos, q]);

  const stats = useMemo(() => {
    if (gastos === initialGastos) return initialStats;
    const total = gastos.reduce((sum, row) => sum + row.monto, 0);
    return { total, count: gastos.length, avg: gastos.length ? total / gastos.length : 0, por_categoria: [] };
  }, [gastos, initialGastos, initialStats]);

  function startCreate() {
    setAdding(true);
    setEditing(null);
    setDraft({ monto: "", fecha: new Date().toISOString().slice(0, 10), categoria: categories[0] || "combustible", vehiculo: "", descripcion: "", cta_retiro_id: "" });
  }

  function startEdit(row: Gasto) {
    setAdding(false);
    setEditing(row.folio);
    setDraft({
      folio: row.folio,
      monto: String(row.monto),
      fecha: row.fecha,
      categoria: row.categoria || categories[0] || "combustible",
      vehiculo: row.vehiculo || "",
      descripcion: row.descripcion || "",
      cta_retiro_id: row.cta_retiro_id || ""
    });
  }

  async function save(action: "create" | "update") {
    setSaving(true);
    setError("");
    const res = await fetch("/api/gastos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...draft, monto: Number(draft.monto || 0) })
    });
    const json = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok || json.ok === false) {
      setError(json.error || "No se pudo guardar");
      return;
    }
    if (action === "create" && json.gasto) setGastos((rows) => [json.gasto, ...rows]);
    if (action === "update") {
      const account = bankAccounts.find((item) => item.id === draft.cta_retiro_id);
      setGastos((rows) =>
        rows.map((row) =>
          row.folio === draft.folio
            ? { ...row, monto: Number(draft.monto || 0), fecha: draft.fecha, categoria: draft.categoria, vehiculo: draft.vehiculo || null, descripcion: draft.descripcion, cta_retiro_id: account?.id || null, cta_retiro_nombre: account?.account_name || null, cta_retiro_folio: account?.folio || null }
            : row
        )
      );
    }
    setAdding(false);
    setEditing(null);
  }

  async function remove(folio: string) {
    if (!confirm(`Eliminar ${folio}?`)) return;
    setSaving(true);
    setError("");
    const res = await fetch("/api/gastos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", folio })
    });
    const json = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok || json.ok === false) {
      setError(json.error || "No se pudo eliminar");
      return;
    }
    setGastos((rows) => rows.filter((row) => row.folio !== folio));
  }

  function downloadCsv() {
    const blob = new Blob([csv(filtered)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gastos-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="grid gap-3 md:grid-cols-3">
        <Kpi label="Gasto total" value={mxn(stats.total)} />
        <Kpi label="Movimientos" value={String(stats.count)} />
        <Kpi label="Promedio" value={mxn(stats.avg)} />
      </div>

      <section className="mt-5 rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[240px] flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
            <input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Buscar gasto, folio, categoria..." className="w-full rounded-md border border-border bg-bg py-2 pl-9 pr-3 text-sm text-slate-100 placeholder-muted outline-none focus:border-primary" />
          </div>
          <span className="text-xs text-muted">{filtered.length} registros</span>
          <button onClick={startCreate} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90">
            <Plus size={15} /> Nuevo
          </button>
          <button onClick={downloadCsv} className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50">
            <Download size={15} /> CSV
          </button>
        </div>

        {error ? <p className="mt-3 rounded-md border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p> : null}
        {adding ? <DraftRow draft={draft} setDraft={setDraft} categories={categories} bankAccounts={bankAccounts} onCancel={() => setAdding(false)} onSave={() => save("create")} saving={saving} /> : null}

        <div className="mt-4 overflow-x-auto rounded-md border border-border">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-slate-900/60 text-left text-xs uppercase text-muted">
              <tr>
                {["Folio", "Fecha", "Categoria", "Vehiculo", "Cta retiro", "Descripcion", "Usuario", "Monto", ""].map((head) => (
                  <th key={head} className="px-3 py-3 font-semibold tracking-wide">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50 bg-card">
              {filtered.map((row) => (
                editing === row.folio ? (
                  <tr key={row.folio}>
                    <td colSpan={9} className="p-0">
                      <DraftRow draft={draft} setDraft={setDraft} categories={categories} bankAccounts={bankAccounts} onCancel={() => setEditing(null)} onSave={() => save("update")} saving={saving} />
                    </td>
                  </tr>
                ) : (
                  <tr key={row.folio} className="group hover:bg-slate-700/30">
                    <td className="px-3 py-2 font-mono text-xs text-muted">{row.folio}</td>
                    <td className="px-3 py-2 text-slate-300">{row.fecha}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-200">{row.categoria || "—"}</span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{row.vehiculo || "—"}</td>
                    <td className="px-3 py-2 text-slate-400">{row.cta_retiro_nombre || "—"}</td>
                    <td className="max-w-[280px] truncate px-3 py-2 text-slate-200">{row.descripcion || "—"}</td>
                    <td className="px-3 py-2 text-muted">{row.nombre_usuario || "—"}</td>
                    <td className="px-3 py-2 text-right font-semibold text-white">{mxn(row.monto)}</td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button onClick={() => startEdit(row)} className="rounded p-1 text-muted hover:bg-slate-700 hover:text-white" title="Editar"><Pencil size={14} /></button>
                        <button onClick={() => remove(row.folio)} className="rounded p-1 text-muted hover:bg-red-900/50 hover:text-red-400" title="Eliminar"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function DraftRow({
  draft,
  setDraft,
  categories,
  bankAccounts,
  onCancel,
  onSave,
  saving
}: {
  draft: Draft;
  setDraft: (fn: (draft: Draft) => Draft) => void;
  categories: string[];
  bankAccounts: BankAccount[];
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  const inputCls = "rounded border border-border bg-slate-800 px-2 py-2 text-sm text-slate-100 placeholder-muted focus:border-primary focus:outline-none";
  return (
    <div className="mt-3 rounded-md border border-primary/30 bg-primary/5 p-3">
      <div className="grid gap-2 md:grid-cols-[120px_150px_180px_150px_200px_1fr_auto]">
        <input value={draft.monto} onChange={(event) => setDraft((d) => ({ ...d, monto: event.target.value }))} type="number" placeholder="Monto" className={inputCls} />
        <input value={draft.fecha} onChange={(event) => setDraft((d) => ({ ...d, fecha: event.target.value }))} type="date" className={inputCls} />
        <select value={draft.categoria} onChange={(event) => setDraft((d) => ({ ...d, categoria: event.target.value }))} className={inputCls}>
          {categories.map((category) => <option key={category}>{category}</option>)}
        </select>
        <input value={draft.vehiculo} onChange={(event) => setDraft((d) => ({ ...d, vehiculo: event.target.value }))} placeholder="Vehiculo" className={inputCls} />
        <select value={draft.cta_retiro_id} onChange={(event) => setDraft((d) => ({ ...d, cta_retiro_id: event.target.value }))} className={inputCls}>
          <option value="">Sin cuenta</option>
          {bankAccounts.map((account) => <option key={account.id} value={account.id}>{account.account_name}</option>)}
        </select>
        <input value={draft.descripcion} onChange={(event) => setDraft((d) => ({ ...d, descripcion: event.target.value }))} placeholder="Descripcion" className={inputCls} />
        <div className="flex gap-1">
          <button disabled={saving} onClick={onSave} className="inline-flex h-9 w-9 items-center justify-center rounded bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50" title="Guardar"><Check size={15} /></button>
          <button onClick={onCancel} className="inline-flex h-9 w-9 items-center justify-center rounded border border-border bg-slate-800 text-slate-300 hover:bg-slate-700" title="Cancelar"><X size={15} /></button>
        </div>
      </div>
    </div>
  );
}
