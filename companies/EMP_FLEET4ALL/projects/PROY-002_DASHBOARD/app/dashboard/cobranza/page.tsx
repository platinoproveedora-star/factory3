"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function CobranzaPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps } = useFleetOps(selectedCompanyId, ["trips", "receivables", "payments"]);
  const [payForm, setPayForm] = useState({ trip_folio: "", amount: "", payment_date: "", method: "transfer" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  const [stFilters, setStFilters] = useState({ customer: "", from: "", to: "" });
  const [statement, setStatement] = useState<any>(null);
  const [loadingStatement, setLoadingStatement] = useState(false);
  const pendingReceivables = (ops.receivables || []).filter((row: any) => Number(row.balance || 0) > 0);
  const payments = ops.payments || [];
  const paidTrips = (ops.trips || []).filter((trip: any) => String(trip.payment_status || "").toLowerCase() === "paid");

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
      setStatus(`Pago ${data.data?.payment?.payment_folio} registrado.${data.data?.warnings?.length ? " (" + data.data.warnings.join("; ") + ")" : ""}`);
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
              <div><label className="label">Folio de viaje</label><input list="payment-trips" className="input font-mono" placeholder="T-0001" value={payForm.trip_folio} onChange={(e) => setPayForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} required /></div>
              <datalist id="payment-trips">
                {(ops.trips || []).map((trip: any) => <option key={trip.trip_folio} value={trip.trip_folio}>{trip.customer || trip.trip_folio}</option>)}
              </datalist>
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
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Estado de cuenta</h2>
            <form onSubmit={handleStatement} className="space-y-3">
              <div><label className="label">Cliente</label><input list="statement-customers" className="input" value={stFilters.customer} onChange={(e) => setStFilters((f) => ({ ...f, customer: e.target.value }))} required /></div>
              <datalist id="statement-customers">
                {Array.from(new Set((ops.trips || []).map((trip: any) => trip.customer).filter(Boolean))).map((customer: any) => <option key={customer} value={customer} />)}
              </datalist>
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
          <div className="card lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">Cuentas por cobrar</h2>
              {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-muted text-xs">
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Viaje</th>
                    <th className="text-left py-2">Cliente</th>
                    <th className="text-left py-2">Vence</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-right py-2">Saldo</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingReceivables.slice(0, 50).map((row: any) => (
                    <tr key={row.receivable_folio} className="border-b border-border/50">
                      <td className="py-2 font-mono">{row.trip_folio || row.receivable_folio}</td>
                      <td className="py-2">{row.customer || "-"}</td>
                      <td className="py-2">{row.due_date || "-"}</td>
                      <td className="py-2">{row.collection_status}</td>
                      <td className="py-2 text-right">{fmt(row.balance, row.currency)}</td>
                    </tr>
                  ))}
                  {!pendingReceivables.length && <tr><td colSpan={5} className="py-6 text-center text-muted">Sin saldos pendientes por cobrar.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">Pagos realizados</h2>
              {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-muted text-xs">
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Folio pago</th>
                    <th className="text-left py-2">Viaje</th>
                    <th className="text-left py-2">Cliente</th>
                    <th className="text-left py-2">Fecha</th>
                    <th className="text-left py-2">Metodo</th>
                    <th className="text-right py-2">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.slice(0, 50).map((row: any) => (
                    <tr key={row.payment_folio} className="border-b border-border/50">
                      <td className="py-2 font-mono">{row.payment_folio}</td>
                      <td className="py-2 font-mono">{row.trip_folio || "-"}</td>
                      <td className="py-2">{row.customer || "-"}</td>
                      <td className="py-2">{row.payment_date || "-"}</td>
                      <td className="py-2">{row.method || "-"}</td>
                      <td className="py-2 text-right">{fmt(row.amount, row.currency)}</td>
                    </tr>
                  ))}
                  {!payments.length && <tr><td colSpan={6} className="py-6 text-center text-muted">Sin pagos registrados.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">Viajes pagados</h2>
              {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-muted text-xs">
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Viaje</th>
                    <th className="text-left py-2">Cliente</th>
                    <th className="text-left py-2">Ruta</th>
                    <th className="text-left py-2">Salida</th>
                    <th className="text-left py-2">Operador</th>
                    <th className="text-left py-2">Unidad</th>
                    <th className="text-right py-2">Venta</th>
                    <th className="text-right py-2">Gastos</th>
                    <th className="text-right py-2">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {paidTrips.slice(0, 50).map((trip: any) => (
                    <tr key={trip.trip_folio} className="border-b border-border/50">
                      <td className="py-2 font-mono">{trip.trip_folio}</td>
                      <td className="py-2">{trip.customer || "-"}</td>
                      <td className="py-2">{trip.origin || "-"} - {trip.destination || "-"}</td>
                      <td className="py-2">{trip.departure_date || "-"}</td>
                      <td className="py-2">{trip.driver_key || "-"}</td>
                      <td className="py-2">{trip.unit_key || "-"}</td>
                      <td className="py-2 text-right">{fmt(trip.sale_price, trip.currency)}</td>
                      <td className="py-2 text-right">{fmt(trip.expenses_total ?? trip.trip_cost ?? 0, trip.currency)}</td>
                      <td className="py-2 text-right">{fmt(trip.live_trip_profit ?? trip.trip_profit ?? 0, trip.currency)}</td>
                    </tr>
                  ))}
                  {!paidTrips.length && <tr><td colSpan={9} className="py-6 text-center text-muted">Sin viajes pagados todavia.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
