"use client";
import { useEffect, useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

function defaultRange() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 30);
  return { from: from.toISOString().slice(0, 10), to: today.toISOString().slice(0, 10) };
}

const emptyForm = { trip_folio: "", amount: "", concept: "", expense_type: "", expense_date: "" };

export default function GastosPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps } = useFleetOps(selectedCompanyId, ["trips"]);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastExpense, setLastExpense] = useState<any>(null);
  const [range, setRange] = useState(defaultRange);
  const [expenses, setExpenses] = useState<any[]>([]);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [editingFolio, setEditingFolio] = useState("");
  const [editForm, setEditForm] = useState(emptyForm);

  async function loadExpenses() {
    if (!selectedCompanyId) return;
    setLoadingExpenses(true);
    setStatus("");
    try {
      const qs = new URLSearchParams({ empresa_id: selectedCompanyId, from: range.from, to: range.to, limit: "200" });
      const res = await fetch(`/api/gastos?${qs.toString()}`);
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al cargar gastos"); return; }
      setExpenses(data.data?.expenses || []);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setLoadingExpenses(false);
    }
  }

  useEffect(() => {
    loadExpenses();
  }, [selectedCompanyId, range.from, range.to]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/gastos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa_id: selectedCompanyId, ...form, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al capturar gasto"); return; }
      setLastExpense(data.data?.expense || null);
      setStatus(`Gasto ${data.data?.expense?.expense_folio} registrado (tipo: ${data.data?.expense?.expense_type}).`);
      setForm(emptyForm);
      await loadExpenses();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(expense: any) {
    setEditingFolio(expense.expense_folio);
    setEditForm({
      trip_folio: expense.trip_folio || "",
      amount: String(expense.amount || ""),
      concept: expense.concept || "",
      expense_type: expense.expense_type || "",
      expense_date: expense.expense_date || "",
    });
  }

  async function saveEdit(expenseFolio: string) {
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/gastos", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa_id: selectedCompanyId, expense_folio: expenseFolio, ...editForm }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al actualizar gasto"); return; }
      setEditingFolio("");
      setStatus(`Gasto ${expenseFolio} actualizado.`);
      await loadExpenses();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function deleteExpense(expenseFolio: string) {
    if (!window.confirm(`Borrar gasto ${expenseFolio}?`)) return;
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/gastos", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa_id: selectedCompanyId, expense_folio: expenseFolio }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al borrar gasto"); return; }
      setStatus(`Gasto ${expenseFolio} borrado.`);
      await loadExpenses();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Gastos</h1>
      <p className="text-muted text-sm mb-6">Captura, busca, modifica y borra gastos de viaje</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="space-y-4">
          <div className="card max-w-lg">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div><label className="label">Concepto</label><input className="input" placeholder="gasolina, caseta, comida..." value={form.concept} onChange={(e) => setForm((f) => ({ ...f, concept: e.target.value }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Monto</label><input type="number" className="input" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
                <div><label className="label">Fecha</label><input type="date" className="input" value={form.expense_date} onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))} /></div>
              </div>
              <div>
                <label className="label">Tipo</label>
                <select className="input" value={form.expense_type} onChange={(e) => setForm((f) => ({ ...f, expense_type: e.target.value }))}>
                  <option value="">Inferir automaticamente</option>
                  <option value="fuel">Combustible</option>
                  <option value="tolls">Casetas</option>
                  <option value="food">Comida</option>
                  <option value="repair">Reparacion</option>
                  <option value="other">Otro</option>
                </select>
              </div>
              <div><label className="label">Folio de viaje (opcional)</label><input list="expense-trips" className="input font-mono" placeholder="T-0001" value={form.trip_folio} onChange={(e) => setForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /></div>
              <datalist id="expense-trips">
                {(ops.trips || []).map((trip: any) => <option key={trip.trip_folio} value={trip.trip_folio}>{trip.customer || trip.trip_folio}</option>)}
              </datalist>
              <p className={form.trip_folio ? "text-muted text-xs" : "text-yellow-300 text-xs"}>{form.trip_folio ? "Este gasto impacta el profit vivo del viaje." : "Sin viaje ligado, el gasto queda registrado pero no impacta profit de un viaje."} {loadingOps ? "Cargando viajes..." : ""}</p>
              <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Guardando..." : "Registrar gasto"}</button>
            </form>
          </div>

          <div className="card">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-4">
              <div>
                <h2 className="font-semibold">Gastos del periodo</h2>
                <p className="text-muted text-xs">Por defecto se muestran los ultimos 30 dias.</p>
              </div>
              <div className="grid grid-cols-2 gap-2 md:w-80">
                <div><label className="label">Desde</label><input type="date" className="input" value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} /></div>
                <div><label className="label">Hasta</label><input type="date" className="input" value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} /></div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-muted text-xs">
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Folio</th>
                    <th className="text-left py-2">Fecha</th>
                    <th className="text-left py-2">Viaje</th>
                    <th className="text-left py-2">Concepto</th>
                    <th className="text-left py-2">Tipo</th>
                    <th className="text-right py-2">Monto</th>
                    <th className="text-right py-2">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((expense) => {
                    const editing = editingFolio === expense.expense_folio;
                    return (
                      <tr key={expense.expense_folio} className="border-b border-border/50 align-top">
                        <td className="py-2 font-mono">{expense.expense_folio}</td>
                        <td className="py-2">{editing ? <input type="date" className="input" value={editForm.expense_date} onChange={(e) => setEditForm((f) => ({ ...f, expense_date: e.target.value }))} /> : (expense.expense_date || "-")}</td>
                        <td className="py-2">{editing ? <input list="expense-trips" className="input font-mono" value={editForm.trip_folio} onChange={(e) => setEditForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /> : <span className="font-mono">{expense.trip_folio || "-"}</span>}</td>
                        <td className="py-2">{editing ? <input className="input" value={editForm.concept} onChange={(e) => setEditForm((f) => ({ ...f, concept: e.target.value }))} /> : (expense.concept || "-")}</td>
                        <td className="py-2">
                          {editing ? (
                            <select className="input" value={editForm.expense_type} onChange={(e) => setEditForm((f) => ({ ...f, expense_type: e.target.value }))}>
                              <option value="fuel">Combustible</option>
                              <option value="tolls">Casetas</option>
                              <option value="food">Comida</option>
                              <option value="repair">Reparacion</option>
                              <option value="other">Otro</option>
                            </select>
                          ) : expense.expense_type}
                        </td>
                        <td className="py-2 text-right">{editing ? <input type="number" className="input text-right" value={editForm.amount} onChange={(e) => setEditForm((f) => ({ ...f, amount: e.target.value }))} /> : fmt(expense.amount, expense.currency)}</td>
                        <td className="py-2 text-right whitespace-nowrap">
                          {editing ? (
                            <>
                              <button type="button" className="btn-primary px-3 py-1 mr-2" onClick={() => saveEdit(expense.expense_folio)} disabled={saving}>Guardar</button>
                              <button type="button" className="btn-ghost px-3 py-1" onClick={() => setEditingFolio("")}>Cancelar</button>
                            </>
                          ) : (
                            <>
                              <button type="button" className="btn-ghost px-2 py-1 mr-2" title="Modificar" aria-label="Modificar" onClick={() => startEdit(expense)}>✎</button>
                              <button type="button" className="btn-ghost px-2 py-1 text-red-300" title="Borrar" aria-label="Borrar" onClick={() => deleteExpense(expense.expense_folio)}>🗑</button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {!expenses.length && <tr><td colSpan={7} className="py-6 text-center text-muted">{loadingExpenses ? "Cargando..." : "Sin gastos en el periodo."}</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}

      {lastExpense && (
        <div className="card mt-6 max-w-lg">
          <h2 className="font-semibold mb-3">Ultimo gasto</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><p className="text-muted text-xs">Folio</p><p className="font-mono">{lastExpense.expense_folio}</p></div>
            <div><p className="text-muted text-xs">Tipo</p><p>{lastExpense.expense_type}</p></div>
            <div><p className="text-muted text-xs">Monto</p><p>{fmt(lastExpense.amount, lastExpense.currency)}</p></div>
            <div><p className="text-muted text-xs">Viaje</p><p className="font-mono">{lastExpense.trip_folio || "-"}</p></div>
          </div>
        </div>
      )}
    </div>
  );
}
