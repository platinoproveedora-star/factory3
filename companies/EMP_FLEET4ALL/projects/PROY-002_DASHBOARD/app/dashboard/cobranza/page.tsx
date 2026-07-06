"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function CobranzaPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const [payForm, setPayForm] = useState({ trip_folio: "", amount: "", payment_date: "", method: "transfer" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [receivable, setReceivable] = useState<any>(null);

  const [stFilters, setStFilters] = useState({ customer: "", from: "", to: "" });
  const [statement, setStatement] = useState<any>(null);
  const [loadingStatement, setLoadingStatement] = useState(false);

  async function handlePayment(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/cobranza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "payment", empresa_id: selectedCompanyId, ...payForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al registrar pago"); return; }
      setStatus(`Pago ${data.data?.payment?.payment_folio} registrado.`);

      const syncRes = await fetch("/api/cobranza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "sync", empresa_id: selectedCompanyId, trip_folio: payForm.trip_folio, dry_run: false }),
      });
      const syncData = await syncRes.json();
      if (syncData.ok) setReceivable(syncData.data?.receivable || null);
      setPayForm({ trip_folio: "", amount: "", payment_date: "", method: "transfer" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatement(e: React.FormEvent) {
    e.preventDefault();
    setLoadingStatement(true);
    setStatement(null);
    try {
      const res = await fetch("/api/cobranza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "statement", empresa_id: selectedCompanyId, customer: stFilters.customer,
          period: { from: stFilters.from || null, to: stFilters.to || null }, dry_run: true,
        }),
      });
      const data = await res.json();
      if (data.ok) setStatement(data.data?.statement || null);
      else setStatus(data.error || "Error al generar estado de cuenta");
    } catch {
      setStatus("Error de conexion");
    } finally {
      setLoadingStatement(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Cobranza</h1>
      <p className="text-muted text-sm mb-6">Pagos, cuentas por cobrar y estado de cuenta por cliente</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold mb-4">Registrar pago</h2>
            <form onSubmit={handlePayment} className="space-y-3">
              <div><label className="label">Folio de viaje</label><input className="input font-mono" placeholder="T-0001" value={payForm.trip_folio} onChange={(e) => setPayForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Monto</label><input type="number" className="input" value={payForm.amount} onChange={(e) => setPayForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
                <div><label className="label">Fecha</label><input type="date" className="input" value={payForm.payment_date} onChange={(e) => setPayForm((f) => ({ ...f, payment_date: e.target.value }))} /></div>
              </div>
              <div>
                <label className="label">Metodo</label>
                <select className="input" value={payForm.method} onChange={(e) => setPayForm((f) => ({ ...f, method: e.target.value }))}>
                  <option value="transfer">Transferencia</option>
                  <option value="cash">Efectivo</option>
                  <option value="check">Cheque</option>
                  <option value="card">Tarjeta</option>
                </select>
              </div>
              <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Guardando..." : "Registrar pago"}</button>
            </form>
            {receivable && (
              <div className="mt-4 pt-4 border-t border-border text-sm space-y-1">
                <p><span className="text-muted">Saldo:</span> {fmt(receivable.balance, receivable.currency)}</p>
                <p><span className="text-muted">Status:</span> {receivable.collection_status}</p>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Estado de cuenta</h2>
            <form onSubmit={handleStatement} className="space-y-3">
              <div><label className="label">Cliente</label><input className="input" value={stFilters.customer} onChange={(e) => setStFilters((f) => ({ ...f, customer: e.target.value }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Desde</label><input type="date" className="input" value={stFilters.from} onChange={(e) => setStFilters((f) => ({ ...f, from: e.target.value }))} /></div>
                <div><label className="label">Hasta</label><input type="date" className="input" value={stFilters.to} onChange={(e) => setStFilters((f) => ({ ...f, to: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn-ghost w-full" disabled={loadingStatement}>{loadingStatement ? "Generando..." : "Ver estado de cuenta"}</button>
            </form>
            {statement && (
              <div className="mt-4 pt-4 border-t border-border text-sm">
                <p className="font-semibold mb-2">Total: {fmt(statement.total_balance, statement.currency)}</p>
                {statement.lines.map((l: any) => (
                  <div key={l.trip_folio} className="flex justify-between text-xs py-1 border-b border-border/50">
                    <span className="font-mono">{l.trip_folio}</span>
                    <span>{fmt(l.balance, statement.currency)}</span>
                  </div>
                ))}
                {statement.lines.length === 0 && <p className="text-muted text-xs">Sin viajes para este cliente/periodo.</p>}
              </div>
            )}
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
