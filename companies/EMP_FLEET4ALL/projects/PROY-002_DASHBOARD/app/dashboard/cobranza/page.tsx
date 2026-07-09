"use client";
import { useMemo, useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

const METHOD_LABEL: Record<string, string> = { transfer: "Transferencia", cash: "Efectivo", check: "Cheque", card: "Tarjeta" };

const emptyPaymentEdit = { amount: "", payment_date: "", method: "transfer" };

export default function CobranzaPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps, refetch } = useFleetOps(selectedCompanyId, ["trips", "receivables", "payments"]);
  const [payForm, setPayForm] = useState({ trip_folio: "", amount: "", payment_date: "", method: "transfer" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  const [stFilters, setStFilters] = useState({ customer: "", from: "", to: "" });
  const [statement, setStatement] = useState<any>(null);
  const [loadingStatement, setLoadingStatement] = useState(false);

  const [editingPayment, setEditingPayment] = useState("");
  const [paymentEdit, setPaymentEdit] = useState(emptyPaymentEdit);

  const pendingReceivables = (ops.receivables || []).filter((row: any) => Number(row.balance || 0) > 0);
  const payments = ops.payments || [];
  const paidTrips = (ops.trips || []).filter((trip: any) => ["paid", "partial"].includes(String(trip.payment_status || "").toLowerCase()));

  const tripByFolio = useMemo(() => {
    const map: Record<string, any> = {};
    for (const t of ops.trips || []) map[t.trip_folio] = t;
    return map;
  }, [ops.trips]);

  const receivableByTrip = useMemo(() => {
    const map: Record<string, any> = {};
    for (const r of ops.receivables || []) map[r.trip_folio] = r;
    return map;
  }, [ops.receivables]);

  function route(tripFolio: string) {
    const t = tripByFolio[tripFolio];
    if (!t) return "-";
    return `${t.origin || "-"} - ${t.destination || "-"}`;
  }

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
      refetch?.();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  function startEditPayment(payment: any) {
    setEditingPayment(payment.payment_folio);
    setPaymentEdit({ amount: String(payment.amount || ""), payment_date: payment.payment_date || "", method: payment.method || "transfer" });
    setStatus("");
  }

  async function saveEditPayment(paymentFolio: string) {
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/cobranza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "payment_update", empresa_id: selectedCompanyId, payment_folio: paymentFolio, ...paymentEdit }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al actualizar pago"); return; }
      setEditingPayment("");
      setStatus(`Pago ${paymentFolio} actualizado.`);
      refetch?.();
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function cancelPayment(payment: any) {
    if (!window.confirm(`¿Cancelar el pago ${payment.payment_folio} por ${fmt(payment.amount, payment.currency)}? El saldo pendiente del viaje se restaura.`)) return;
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/cobranza", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "payment_cancel", empresa_id: selectedCompanyId, payment_folio: payment.payment_folio }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al cancelar pago"); return; }
      setStatus(`Pago ${payment.payment_folio} cancelado.`);
      refetch?.();
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

  const paidTripsTotals = paidTrips.reduce(
    (acc: any, t: any) => {
      const receivable = receivableByTrip[t.trip_folio];
      const paid = receivable ? Number(receivable.paid_amount || 0) : Number(t.sale_price || 0);
      const pending = receivable ? Number(receivable.balance || 0) : 0;
      return {
        sale: acc.sale + Number(t.sale_price || 0),
        paid: acc.paid + paid,
        pending: acc.pending + pending,
        expenses: acc.expenses + Number(t.expenses_total ?? t.trip_cost ?? 0),
        profit: acc.profit + Number(t.live_trip_profit ?? t.trip_profit ?? 0),
      };
    },
    { sale: 0, paid: 0, pending: 0, expenses: 0, profit: 0 }
  );

  const receivablesTotals = pendingReceivables.reduce(
    (acc: any, r: any) => ({ total: acc.total + Number(r.total_amount || 0), balance: acc.balance + Number(r.balance || 0) }),
    { total: 0, balance: 0 }
  );

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
                    <th className="text-left py-2">Ruta</th>
                    <th className="text-left py-2">Vence</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-right py-2">Total viaje</th>
                    <th className="text-right py-2">Saldo</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingReceivables.slice(0, 50).map((row: any) => (
                    <tr key={row.receivable_folio} className="border-b border-border/50">
                      <td className="py-2 font-mono">{row.trip_folio || row.receivable_folio}</td>
                      <td className="py-2">{row.customer || "-"}</td>
                      <td className="py-2">{route(row.trip_folio)}</td>
                      <td className="py-2">{row.due_date || "-"}</td>
                      <td className="py-2">{row.collection_status}</td>
                      <td className="py-2 text-right">{fmt(row.total_amount, row.currency)}</td>
                      <td className="py-2 text-right font-semibold">{fmt(row.balance, row.currency)}</td>
                    </tr>
                  ))}
                  {!pendingReceivables.length && <tr><td colSpan={7} className="py-6 text-center text-muted">Sin saldos pendientes por cobrar.</td></tr>}
                </tbody>
                {pendingReceivables.length > 0 && (
                  <tfoot>
                    <tr className="border-t border-border">
                      <td colSpan={5} className="py-2 text-xs font-semibold text-muted">Total</td>
                      <td className="py-2 text-right font-bold">{fmt(receivablesTotals.total)}</td>
                      <td className="py-2 text-right font-bold text-primary">{fmt(receivablesTotals.balance)}</td>
                    </tr>
                  </tfoot>
                )}
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
                    <th className="text-left py-2">Ruta</th>
                    <th className="text-left py-2">Cliente</th>
                    <th className="text-left py-2">Fecha</th>
                    <th className="text-left py-2">Metodo</th>
                    <th className="text-right py-2">Monto</th>
                    <th className="text-right py-2">Total viaje</th>
                    <th className="text-right py-2">Saldo pendiente</th>
                    <th className="text-right py-2">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.slice(0, 50).map((row: any) => {
                    const cancelled = row.status === "cancelled";
                    const editing = editingPayment === row.payment_folio;
                    const receivable = receivableByTrip[row.trip_folio];
                    return (
                      <tr key={row.payment_folio} className={`border-b border-border/50 ${cancelled ? "opacity-50" : ""}`}>
                        <td className="py-2 font-mono">{row.payment_folio}</td>
                        <td className="py-2 font-mono">{row.trip_folio || "-"}</td>
                        <td className="py-2">{route(row.trip_folio)}</td>
                        <td className="py-2">{row.customer || "-"}</td>
                        <td className="py-2">{editing ? <input type="date" className="input" value={paymentEdit.payment_date} onChange={(e) => setPaymentEdit((f) => ({ ...f, payment_date: e.target.value }))} /> : (row.payment_date || "-")}</td>
                        <td className="py-2">
                          {editing ? (
                            <select className="input" value={paymentEdit.method} onChange={(e) => setPaymentEdit((f) => ({ ...f, method: e.target.value }))}>
                              <option value="transfer">Transferencia</option>
                              <option value="cash">Efectivo</option>
                              <option value="check">Cheque</option>
                              <option value="card">Tarjeta</option>
                            </select>
                          ) : (METHOD_LABEL[row.method] || row.method || "-")}
                        </td>
                        <td className="py-2 text-right">{editing ? <input type="number" className="input text-right" value={paymentEdit.amount} onChange={(e) => setPaymentEdit((f) => ({ ...f, amount: e.target.value }))} /> : fmt(row.amount, row.currency)}</td>
                        <td className="py-2 text-right text-muted">{receivable ? fmt(receivable.total_amount, row.currency) : "-"}</td>
                        <td className="py-2 text-right text-muted">{receivable ? fmt(receivable.balance, row.currency) : "-"}</td>
                        <td className="py-2 text-right whitespace-nowrap">
                          {cancelled ? (
                            <span className="text-xs text-red-400 font-semibold">Cancelado</span>
                          ) : editing ? (
                            <>
                              <button type="button" className="btn-primary px-3 py-1 mr-2" onClick={() => saveEditPayment(row.payment_folio)} disabled={saving}>Guardar</button>
                              <button type="button" className="btn-ghost px-3 py-1" onClick={() => setEditingPayment("")}>Cancelar</button>
                            </>
                          ) : (
                            <>
                              <button type="button" className="btn-ghost px-2 py-1 mr-2" title="Modificar" aria-label="Modificar" onClick={() => startEditPayment(row)}>✎</button>
                              <button type="button" className="btn-ghost px-2 py-1 text-red-300" title="Cancelar pago" aria-label="Cancelar pago" onClick={() => cancelPayment(row)} disabled={saving}>🗑</button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {!payments.length && <tr><td colSpan={10} className="py-6 text-center text-muted">Sin pagos registrados.</td></tr>}
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
                    <th className="text-right py-2">Importe pagado</th>
                    <th className="text-right py-2">Saldo</th>
                    <th className="text-right py-2">Gastos</th>
                    <th className="text-right py-2">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {paidTrips.slice(0, 50).map((trip: any) => {
                    const receivable = receivableByTrip[trip.trip_folio];
                    return (
                      <tr key={trip.trip_folio} className="border-b border-border/50">
                        <td className="py-2 font-mono">{trip.trip_folio}</td>
                        <td className="py-2">{trip.customer || "-"}</td>
                        <td className="py-2">{trip.origin || "-"} - {trip.destination || "-"}</td>
                        <td className="py-2">{trip.departure_date || "-"}</td>
                        <td className="py-2">{trip.driver_key || "-"}</td>
                        <td className="py-2">{trip.unit_key || "-"}</td>
                        <td className="py-2 text-right">{fmt(trip.sale_price, trip.currency)}</td>
                        <td className="py-2 text-right">{receivable ? fmt(receivable.paid_amount, trip.currency) : fmt(trip.sale_price, trip.currency)}</td>
                        <td className={`py-2 text-right ${receivable && receivable.balance > 0 ? "text-yellow-300 font-semibold" : ""}`}>{receivable ? fmt(receivable.balance, trip.currency) : fmt(0, trip.currency)}</td>
                        <td className="py-2 text-right">{fmt(trip.expenses_total ?? trip.trip_cost ?? 0, trip.currency)}</td>
                        <td className="py-2 text-right">{fmt(trip.live_trip_profit ?? trip.trip_profit ?? 0, trip.currency)}</td>
                      </tr>
                    );
                  })}
                  {!paidTrips.length && <tr><td colSpan={11} className="py-6 text-center text-muted">Sin viajes pagados todavia.</td></tr>}
                </tbody>
                {paidTrips.length > 0 && (
                  <tfoot>
                    <tr className="border-t border-border">
                      <td colSpan={6} className="py-2 text-xs font-semibold text-muted">Total</td>
                      <td className="py-2 text-right font-bold">{fmt(paidTripsTotals.sale)}</td>
                      <td className="py-2 text-right font-bold">{fmt(paidTripsTotals.paid)}</td>
                      <td className="py-2 text-right font-bold text-yellow-300">{fmt(paidTripsTotals.pending)}</td>
                      <td className="py-2 text-right font-bold">{fmt(paidTripsTotals.expenses)}</td>
                      <td className="py-2 text-right font-bold text-primary">{fmt(paidTripsTotals.profit)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
