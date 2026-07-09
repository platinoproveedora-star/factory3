"use client";
import { useEffect, useMemo, useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });
const cap = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

const MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function monthKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function last3MonthKeys() {
  const now = new Date();
  return [0, 1, 2].map((i) => monthKey(new Date(now.getFullYear(), now.getMonth() - i, 1)));
}

function monthLabel(key: string) {
  const [y, m] = key.split("-");
  return `${MONTH_NAMES[Number(m) - 1]} ${y}`;
}

type Category = { id: string; nombre: string; activo: boolean };
type Expense = {
  expense_folio: string;
  trip_folio?: string | null;
  amount: number;
  concept?: string;
  expense_type?: string;
  expense_date?: string;
  currency?: string;
};

const emptyForm = { trip_folio: "", amount: "", concept: "", expense_type: "", expense_date: "" };

export default function GastosPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps } = useFleetOps(selectedCompanyId, ["trips"]);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastExpense, setLastExpense] = useState<any>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [editingFolio, setEditingFolio] = useState("");
  const [editForm, setEditForm] = useState(emptyForm);

  const [categorias, setCategorias] = useState<Category[]>([]);
  const [manageCats, setManageCats] = useState(false);
  const [newCatName, setNewCatName] = useState("");
  const [catSaving, setCatSaving] = useState(false);
  const [catError, setCatError] = useState("");

  const monthKeys = useMemo(last3MonthKeys, []);
  const ACTIVE_CATEGORIES = useMemo(() => categorias.filter((c) => c.activo).map((c) => c.nombre), [categorias]);

  async function loadCategorias() {
    if (!selectedCompanyId) return;
    try {
      const res = await fetch(`/api/gastos/categorias?empresa_id=${encodeURIComponent(selectedCompanyId)}`);
      const data = await res.json();
      if (data.ok) setCategorias(data.data?.categorias || []);
    } catch {
      /* silencioso, no bloquea el resto de la pantalla */
    }
  }

  async function loadExpenses() {
    if (!selectedCompanyId) return;
    setLoadingExpenses(true);
    setStatus("");
    try {
      const from = `${monthKeys[monthKeys.length - 1]}-01`;
      const qs = new URLSearchParams({ empresa_id: selectedCompanyId, from, limit: "500" });
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
    loadCategorias();
    loadExpenses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCompanyId]);

  async function addCategory() {
    const nombre = newCatName.trim();
    if (!nombre || !selectedCompanyId) return;
    setCatSaving(true); setCatError("");
    try {
      const res = await fetch("/api/gastos/categorias", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create", empresa_id: selectedCompanyId, nombre }),
      });
      const data = await res.json();
      if (!data.ok) { setCatError(data.error || "Error al crear categoría"); return; }
      const categoria: Category = data.data?.categoria;
      setCategorias((prev) => {
        const exists = prev.some((c) => c.id === categoria.id);
        return exists ? prev.map((c) => (c.id === categoria.id ? categoria : c)) : [...prev, categoria];
      });
      setNewCatName("");
    } catch {
      setCatError("Error de conexion");
    } finally {
      setCatSaving(false);
    }
  }

  async function toggleCategory(cat: Category) {
    if (!selectedCompanyId) return;
    setCatSaving(true); setCatError("");
    try {
      const res = await fetch("/api/gastos/categorias", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "toggle", empresa_id: selectedCompanyId, id: cat.id, activo: !cat.activo }),
      });
      const data = await res.json();
      if (!data.ok) { setCatError(data.error || "Error al actualizar categoría"); return; }
      const categoria: Category = data.data?.categoria;
      setCategorias((prev) => prev.map((c) => (c.id === categoria.id ? categoria : c)));
    } catch {
      setCatError("Error de conexion");
    } finally {
      setCatSaving(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.expense_type) { setStatus("Elige una categoría"); return; }
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
      setStatus(`Gasto ${data.data?.expense?.expense_folio} registrado (categoría: ${data.data?.expense?.expense_type}).`);
      setForm(emptyForm);
      await loadExpenses();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(expense: Expense) {
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

  const expensesByMonth = useMemo(() => {
    const buckets: Record<string, Expense[]> = {};
    for (const key of monthKeys) buckets[key] = [];
    for (const e of expenses) {
      const key = (e.expense_date || "").slice(0, 7);
      if (buckets[key]) buckets[key].push(e);
    }
    for (const key of monthKeys) buckets[key].sort((a, b) => (b.expense_date || "").localeCompare(a.expense_date || ""));
    return buckets;
  }, [expenses, monthKeys]);

  const categoryMonthly = useMemo(() => {
    const matrix: Record<string, Record<string, number>> = {};
    const catSet = new Set<string>();
    for (const e of expenses) {
      const mKey = (e.expense_date || "").slice(0, 7);
      if (!monthKeys.includes(mKey)) continue;
      const cat = e.expense_type || "otro";
      catSet.add(cat);
      if (!matrix[cat]) matrix[cat] = {};
      matrix[cat][mKey] = (matrix[cat][mKey] || 0) + Number(e.amount || 0);
    }
    const cats = Array.from(catSet).sort((a, b) => {
      const ta = Object.values(matrix[a] || {}).reduce((s, v) => s + v, 0);
      const tb = Object.values(matrix[b] || {}).reduce((s, v) => s + v, 0);
      return tb - ta;
    });
    return { matrix, cats };
  }, [expenses, monthKeys]);

  if (loadingCompany) return null;

  const inputCls = "input";

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Gastos</h1>
      <p className="text-muted text-sm mb-6">Captura, busca, modifica y borra gastos de viaje por categoría</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">Nuevo gasto</h2>
                <button type="button" onClick={() => { setManageCats((v) => !v); setCatError(""); }} className="text-xs text-muted hover:text-fg">
                  {manageCats ? "Cerrar categorías" : "Categorías"}
                </button>
              </div>

              {manageCats && (
                <div className="mb-4 rounded-lg border border-primary/40 bg-primary/5 p-3">
                  <p className="mb-2 text-xs font-semibold text-primary">Categorías de gasto</p>
                  {catError && <div className="mb-2 rounded border border-red-800 bg-red-900/20 text-red-300 text-xs px-2 py-1">{catError}</div>}
                  <div className="mb-3 flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Nueva categoría"
                      value={newCatName}
                      onChange={(e) => setNewCatName(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCategory(); } }}
                      className="input flex-1"
                    />
                    <button type="button" onClick={addCategory} disabled={catSaving || !newCatName.trim()} className="btn-primary px-3 py-1.5 disabled:opacity-40">+ Agregar</button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {categorias.length === 0 && <span className="text-xs text-muted">Sin categorías configuradas todavía.</span>}
                    {categorias.map((c) => (
                      <span key={c.id} className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs ${c.activo ? "bg-slate-700 text-slate-200" : "bg-slate-800 text-slate-500 line-through"}`}>
                        {c.nombre}
                        <button type="button" onClick={() => toggleCategory(c)} disabled={catSaving} title={c.activo ? "Quitar" : "Reactivar"} className="hover:opacity-70 disabled:opacity-40">
                          {c.activo ? "✕" : "↺"}
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-3">
                <div><label className="label">Concepto</label><input className={inputCls} placeholder="gasolina, caseta, comida..." value={form.concept} onChange={(e) => setForm((f) => ({ ...f, concept: e.target.value }))} required /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Monto</label><input type="number" className={inputCls} value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
                  <div><label className="label">Fecha</label><input type="date" className={inputCls} value={form.expense_date} onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))} /></div>
                </div>
                <div>
                  <label className="label">Categoría</label>
                  <select className={inputCls} value={form.expense_type} onChange={(e) => setForm((f) => ({ ...f, expense_type: e.target.value }))} required>
                    <option value="">Selecciona una categoría...</option>
                    {ACTIVE_CATEGORIES.map((c) => <option key={c} value={c}>{cap(c)}</option>)}
                  </select>
                  {!ACTIVE_CATEGORIES.length && <p className="text-yellow-300 text-xs mt-1">Sin categorías dadas de alta — abre "Categorías" arriba para crear la primera.</p>}
                </div>
                <div><label className="label">Folio de viaje (opcional)</label><input list="expense-trips" className={inputCls + " font-mono"} placeholder="T-0001" value={form.trip_folio} onChange={(e) => setForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /></div>
                <datalist id="expense-trips">
                  {(ops.trips || []).map((trip: any) => <option key={trip.trip_folio} value={trip.trip_folio}>{trip.customer || trip.trip_folio}</option>)}
                </datalist>
                <p className={form.trip_folio ? "text-muted text-xs" : "text-yellow-300 text-xs"}>{form.trip_folio ? "Este gasto impacta el profit vivo del viaje." : "Sin viaje ligado, el gasto queda registrado pero no impacta profit de un viaje."} {loadingOps ? "Cargando viajes..." : ""}</p>
                <button type="submit" className="btn-primary w-full" disabled={saving || !ACTIVE_CATEGORIES.length}>{saving ? "Guardando..." : "Registrar gasto"}</button>
              </form>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">Totales por categoría — últimos 3 meses</h2>
                {loadingExpenses && <span className="text-muted text-xs">Cargando...</span>}
              </div>
              {!categoryMonthly.cats.length ? (
                <p className="py-8 text-center text-sm text-muted">Sin gastos en este periodo.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-muted text-xs">
                      <tr className="border-b border-border">
                        <th className="text-left py-2">Categoría</th>
                        {monthKeys.map((k) => (
                          <th key={k} className={`text-right py-2 ${k === monthKeys[0] ? "text-primary" : ""}`}>{monthLabel(k)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {categoryMonthly.cats.map((cat) => (
                        <tr key={cat} className="border-b border-border/50">
                          <td className="py-2">{cap(cat)}</td>
                          {monthKeys.map((k) => {
                            const val = categoryMonthly.matrix[cat]?.[k] || 0;
                            return <td key={k} className="py-2 text-right">{val > 0 ? fmt(val) : <span className="text-border">—</span>}</td>;
                          })}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-border">
                        <td className="py-2 text-xs font-semibold text-muted">Total mes</td>
                        {monthKeys.map((k) => {
                          const total = categoryMonthly.cats.reduce((s, c) => s + (categoryMonthly.matrix[c]?.[k] || 0), 0);
                          return <td key={k} className={`py-2 text-right font-bold ${k === monthKeys[0] ? "text-primary" : "text-slate-300"}`}>{fmt(total)}</td>;
                        })}
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </div>
          </div>

          {status && <p className="text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}

          {monthKeys.map((key) => (
            <MonthExpenseTable
              key={key}
              title={key === monthKeys[0] ? `${monthLabel(key)} (mes actual)` : monthLabel(key)}
              expenses={expensesByMonth[key] || []}
              categorias={ACTIVE_CATEGORIES}
              editingFolio={editingFolio}
              editForm={editForm}
              setEditForm={setEditForm}
              saving={saving}
              onStartEdit={startEdit}
              onSaveEdit={saveEdit}
              onCancelEdit={() => setEditingFolio("")}
              onDelete={deleteExpense}
              tripsDatalistId="expense-trips"
              loading={loadingExpenses}
            />
          ))}
        </div>
      )}

      {lastExpense && (
        <div className="card mt-6 max-w-lg">
          <h2 className="font-semibold mb-3">Ultimo gasto</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><p className="text-muted text-xs">Folio</p><p className="font-mono">{lastExpense.expense_folio}</p></div>
            <div><p className="text-muted text-xs">Categoría</p><p>{cap(lastExpense.expense_type)}</p></div>
            <div><p className="text-muted text-xs">Monto</p><p>{fmt(lastExpense.amount, lastExpense.currency)}</p></div>
            <div><p className="text-muted text-xs">Viaje</p><p className="font-mono">{lastExpense.trip_folio || "-"}</p></div>
          </div>
        </div>
      )}
    </div>
  );
}

function MonthExpenseTable({
  title, expenses, categorias, editingFolio, editForm, setEditForm, saving,
  onStartEdit, onSaveEdit, onCancelEdit, onDelete, tripsDatalistId, loading,
}: {
  title: string;
  expenses: Expense[];
  categorias: string[];
  editingFolio: string;
  editForm: typeof emptyForm;
  setEditForm: React.Dispatch<React.SetStateAction<typeof emptyForm>>;
  saving: boolean;
  onStartEdit: (e: Expense) => void;
  onSaveEdit: (folio: string) => void;
  onCancelEdit: () => void;
  onDelete: (folio: string) => void;
  tripsDatalistId: string;
  loading: boolean;
}) {
  const total = expenses.reduce((s, e) => s + Number(e.amount || 0), 0);
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold">{title}</h2>
        <span className="text-sm font-bold text-primary">{fmt(total)}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-muted text-xs">
            <tr className="border-b border-border">
              <th className="text-left py-2">Folio</th>
              <th className="text-left py-2">Fecha</th>
              <th className="text-left py-2">Viaje</th>
              <th className="text-left py-2">Concepto</th>
              <th className="text-left py-2">Categoría</th>
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
                  <td className="py-2">{editing ? <input list={tripsDatalistId} className="input font-mono" value={editForm.trip_folio} onChange={(e) => setEditForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /> : <span className="font-mono">{expense.trip_folio || "-"}</span>}</td>
                  <td className="py-2">{editing ? <input className="input" value={editForm.concept} onChange={(e) => setEditForm((f) => ({ ...f, concept: e.target.value }))} /> : (expense.concept || "-")}</td>
                  <td className="py-2">
                    {editing ? (
                      <select className="input" value={editForm.expense_type} onChange={(e) => setEditForm((f) => ({ ...f, expense_type: e.target.value }))}>
                        {categorias.map((c) => <option key={c} value={c}>{cap(c)}</option>)}
                      </select>
                    ) : cap(expense.expense_type || "")}
                  </td>
                  <td className="py-2 text-right">{editing ? <input type="number" className="input text-right" value={editForm.amount} onChange={(e) => setEditForm((f) => ({ ...f, amount: e.target.value }))} /> : fmt(expense.amount, expense.currency)}</td>
                  <td className="py-2 text-right whitespace-nowrap">
                    {editing ? (
                      <>
                        <button type="button" className="btn-primary px-3 py-1 mr-2" onClick={() => onSaveEdit(expense.expense_folio)} disabled={saving}>Guardar</button>
                        <button type="button" className="btn-ghost px-3 py-1" onClick={onCancelEdit}>Cancelar</button>
                      </>
                    ) : (
                      <>
                        <button type="button" className="btn-ghost px-2 py-1 mr-2" title="Modificar" aria-label="Modificar" onClick={() => onStartEdit(expense)}>✎</button>
                        <button type="button" className="btn-ghost px-2 py-1 text-red-300" title="Borrar" aria-label="Borrar" onClick={() => onDelete(expense.expense_folio)}>🗑</button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
            {!expenses.length && <tr><td colSpan={7} className="py-6 text-center text-muted">{loading ? "Cargando..." : "Sin gastos en este mes."}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
