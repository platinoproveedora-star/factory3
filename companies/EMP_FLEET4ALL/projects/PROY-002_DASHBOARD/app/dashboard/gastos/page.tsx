"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function GastosPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const [form, setForm] = useState({ trip_folio: "", amount: "", concept: "", expense_date: "" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastExpense, setLastExpense] = useState<any>(null);

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
      setForm({ trip_folio: "", amount: "", concept: "", expense_date: "" });
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
      <p className="text-muted text-sm mb-6">Captura gastos de viaje (combustible, casetas, comida, taller...)</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="card max-w-lg">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div><label className="label">Concepto</label><input className="input" placeholder="gasolina, caseta, comida..." value={form.concept} onChange={(e) => setForm((f) => ({ ...f, concept: e.target.value }))} required /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Monto</label><input type="number" className="input" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
              <div><label className="label">Fecha</label><input type="date" className="input" value={form.expense_date} onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))} /></div>
            </div>
            <div><label className="label">Folio de viaje (opcional)</label><input className="input font-mono" placeholder="T-0001" value={form.trip_folio} onChange={(e) => setForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /></div>
            <p className="text-muted text-xs">El tipo de gasto (fuel, tolls, food, repair) se infiere del concepto automaticamente.</p>
            <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Guardando..." : "Registrar gasto"}</button>
          </form>
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
