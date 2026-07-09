"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

type Trip = {
  trip_folio?: string;
  customer?: string;
  origin?: string;
  destination?: string;
  departure_date?: string;
  arrival_date?: string;
  sale_price?: number;
  currency?: string;
  trip_cost?: number;
  trip_profit?: number;
  expenses_total?: number;
  live_trip_profit?: number;
  driver_key?: string;
  unit_key?: string;
  distance_km?: number;
  trip_status?: string;
  payment_status?: string;
};

type TripMonth = {
  key: string;
  label: string;
  from: string;
  to: string;
  trips: Trip[];
  totals: {
    count: number;
    sale_price: number;
    expenses: number;
    profit: number;
  };
};

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

const emptyMonthTotals = { count: 0, sale_price: 0, expenses: 0, profit: 0 };

export default function ViajesPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps, error: opsError } = useFleetOps(selectedCompanyId, ["trips", "drivers", "units"]);
  const [form, setForm] = useState({ customer: "", origin: "", destination: "", sale_price: "", departure_date: "", driver_key: "", unit_key: "", distance_km: "", payment_status: "receivable", payment_mode: "credito", payment_method: "transfer", credit_days: "30", paid_amount: "" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastTrip, setLastTrip] = useState<Trip | null>(null);
  const [closeFolio, setCloseFolio] = useState("");
  const [closing, setClosing] = useState(false);
  const [editingFolio, setEditingFolio] = useState("");
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [savingEdit, setSavingEdit] = useState(false);
  const [tripOverrides, setTripOverrides] = useState<Record<string, Trip>>({});
  const [deletedTripFolios, setDeletedTripFolios] = useState<Record<string, boolean>>({});

  const applyLocalTripState = (trip: Trip) => {
    const folio = trip.trip_folio || "";
    const merged = tripOverrides[folio] ? { ...trip, ...tripOverrides[folio] } : trip;
    return deletedTripFolios[folio] ? null : merged;
  };
  const recalcMonth = (month: TripMonth): TripMonth => {
    const rows = (month.trips || []).map(applyLocalTripState).filter(Boolean) as Trip[];
    const sale = rows.reduce((sum, trip) => sum + Number(trip.sale_price || 0), 0);
    const expenses = rows.reduce((sum, trip) => sum + Number(trip.expenses_total ?? trip.trip_cost ?? 0), 0);
    const profit = rows.reduce((sum, trip) => sum + Number(trip.live_trip_profit ?? trip.trip_profit ?? 0), 0);
    return {
      ...month,
      trips: rows,
      totals: {
        count: rows.length,
        sale_price: sale,
        expenses,
        profit,
      },
    };
  };
  const tripMonths = ((ops.trip_months || []) as TripMonth[]).map(recalcMonth);
  const fallbackTrips = ((ops.trips || []) as Trip[]).map(applyLocalTripState).filter(Boolean) as Trip[];
  const monthSections = tripMonths.length
    ? tripMonths
    : [{
        key: "sin-mes",
        label: "Viajes",
        from: "",
        to: "",
        trips: fallbackTrips,
        totals: {
          ...emptyMonthTotals,
          count: fallbackTrips.length,
          sale_price: fallbackTrips.reduce((sum, trip) => sum + Number(trip.sale_price || 0), 0),
          expenses: fallbackTrips.reduce((sum, trip) => sum + Number(trip.expenses_total ?? trip.trip_cost ?? 0), 0),
          profit: fallbackTrips.reduce((sum, trip) => sum + Number(trip.live_trip_profit ?? trip.trip_profit ?? 0), 0),
        },
      }];

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/viajes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create", empresa_id: selectedCompanyId, ...form, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al crear viaje"); return; }
      setLastTrip(data.data?.trip || null);
      const payment = data.data?.collection?.payment?.payment_folio;
      const receivable = data.data?.collection?.receivable?.receivable_folio;
      setStatus(`Viaje ${data.data?.trip?.trip_folio} creado.${payment ? " Pago " + payment + " generado." : ""}${receivable ? " CxC " + receivable + " generada." : ""}`);
      setForm({ customer: "", origin: "", destination: "", sale_price: "", departure_date: "", driver_key: "", unit_key: "", distance_km: "", payment_status: "receivable", payment_mode: "credito", payment_method: "transfer", credit_days: "30", paid_amount: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function handleClose(e: React.FormEvent) {
    e.preventDefault();
    setClosing(true);
    setStatus("");
    try {
      const res = await fetch("/api/viajes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "close", empresa_id: selectedCompanyId, trip_folio: closeFolio, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al cerrar viaje"); return; }
      setLastTrip(data.data?.trip || null);
      setStatus(`Viaje ${closeFolio} cerrado. Profit: ${fmt(data.data?.trip?.trip_profit, data.data?.trip?.currency)}`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setClosing(false);
    }
  }

  function startEdit(trip: Trip) {
    setEditingFolio(trip.trip_folio || "");
    setEditForm({
      customer: trip.customer || "",
      origin: trip.origin || "",
      destination: trip.destination || "",
      departure_date: trip.departure_date || "",
      arrival_date: trip.arrival_date || "",
      sale_price: String(trip.sale_price ?? ""),
      currency: trip.currency || "MXN",
      driver_key: trip.driver_key || "",
      unit_key: trip.unit_key || "",
      distance_km: String(trip.distance_km ?? ""),
      trip_status: trip.trip_status || "active",
    });
    setStatus("");
  }

  async function saveEdit(tripFolio: string) {
    setSavingEdit(true);
    setStatus("");
    try {
      const res = await fetch("/api/viajes", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa_id: selectedCompanyId, trip_folio: tripFolio, ...editForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al actualizar viaje"); return; }
      const updated = data.data?.trip || {};
      setTripOverrides((current) => ({ ...current, [tripFolio]: updated }));
      setEditingFolio("");
      setStatus(`Viaje ${tripFolio} actualizado.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingEdit(false);
    }
  }

  async function deleteTrip(trip: Trip) {
    const tripFolio = trip.trip_folio || "";
    if (!tripFolio) return;
    if (!window.confirm(`Borrar viaje ${tripFolio}? Sus pagos y gastos quedaran libres, sin folio de viaje.`)) return;
    setSavingEdit(true);
    setStatus("");
    try {
      const res = await fetch("/api/viajes", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa_id: selectedCompanyId, trip_folio: tripFolio, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al borrar viaje"); return; }
      setDeletedTripFolios((current) => ({ ...current, [tripFolio]: true }));
      const freed = data.data?.freed || {};
      const deleted = data.data?.deleted || {};
      setStatus(`Viaje ${tripFolio} borrado. Gastos libres: ${freed.expenses || 0}. Pagos libres: ${freed.payments || 0}. CxC eliminadas: ${deleted.receivables || 0}.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingEdit(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Viajes</h1>
      <p className="text-muted text-sm mb-6">Crea, cierra y consulta viajes de la flotilla</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="space-y-4">
        {opsError && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm">{opsError}</div>}
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold mb-4">Nuevo viaje</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div><label className="label">Cliente</label><input className="input" value={form.customer} onChange={(e) => setForm((f) => ({ ...f, customer: e.target.value }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Origen</label><input className="input" value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} required /></div>
                <div><label className="label">Destino</label><input className="input" value={form.destination} onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))} required /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Precio de venta</label><input type="number" className="input" value={form.sale_price} onChange={(e) => setForm((f) => ({ ...f, sale_price: e.target.value }))} required /></div>
                <div><label className="label">Fecha salida</label><input type="date" className="input" value={form.departure_date} onChange={(e) => setForm((f) => ({ ...f, departure_date: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">Operador</label>
                  <input list="fleet-drivers" className="input" value={form.driver_key} onChange={(e) => setForm((f) => ({ ...f, driver_key: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Unidad</label>
                  <input list="fleet-units" className="input" value={form.unit_key} onChange={(e) => setForm((f) => ({ ...f, unit_key: e.target.value }))} />
                </div>
                <div><label className="label">Km</label><input type="number" className="input" value={form.distance_km} onChange={(e) => setForm((f) => ({ ...f, distance_km: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">Status de pago</label>
                  <select className="input" value={form.payment_status} onChange={(e) => setForm((f) => ({ ...f, payment_status: e.target.value, paid_amount: e.target.value === "partial" ? f.paid_amount : "" }))}>
                    <option value="receivable">Por cobrar</option>
                    <option value="paid">Pagado total</option>
                    <option value="partial">Pagado parcial</option>
                  </select>
                </div>
                <div>
                  <label className="label">Forma de pago</label>
                  <select className="input" value={form.payment_mode} onChange={(e) => setForm((f) => ({ ...f, payment_mode: e.target.value, payment_status: e.target.value === "contado" ? "paid" : f.payment_status }))}>
                    <option value="contado">Contado</option>
                    <option value="credito">Credito</option>
                    <option value="cob">Cob</option>
                  </select>
                </div>
                <div>
                  <label className="label">Metodo</label>
                  <select className="input" value={form.payment_method} onChange={(e) => setForm((f) => ({ ...f, payment_method: e.target.value }))}>
                    <option value="transfer">Transferencia</option>
                    <option value="cash">Efectivo</option>
                    <option value="check">Cheque</option>
                    <option value="card">Tarjeta</option>
                  </select>
                </div>
              </div>
              {(form.payment_mode === "credito" || form.payment_mode === "cob" || form.payment_status === "partial") && (
                <div className="grid grid-cols-2 gap-3">
                  {(form.payment_mode === "credito" || form.payment_mode === "cob") && <div><label className="label">Dias de credito</label><input type="number" className="input" value={form.credit_days} onChange={(e) => setForm((f) => ({ ...f, credit_days: e.target.value }))} /></div>}
                  {form.payment_status === "partial" && <div><label className="label">Monto pagado</label><input type="number" className="input" value={form.paid_amount} onChange={(e) => setForm((f) => ({ ...f, paid_amount: e.target.value }))} required /></div>}
                </div>
              )}
              <datalist id="fleet-drivers">
                {(ops.drivers || []).map((driver: any) => <option key={driver.driver_key} value={driver.driver_key}>{driver.full_name || driver.driver_key}</option>)}
              </datalist>
              <datalist id="fleet-units">
                {(ops.units || []).map((unit: any) => <option key={unit.unit_key} value={unit.unit_key}>{unit.plate || unit.unit_key}</option>)}
              </datalist>
              <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Guardando..." : "Crear viaje"}</button>
            </form>
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Cerrar viaje</h2>
            <form onSubmit={handleClose} className="space-y-3">
              <div><label className="label">Folio del viaje</label><input className="input font-mono" placeholder="T-0001" value={closeFolio} onChange={(e) => setCloseFolio(e.target.value.toUpperCase())} required /></div>
              <p className="text-muted text-xs">Recalcula trip_cost (suma de gastos) y trip_profit automaticamente.</p>
              <button type="submit" className="btn-ghost w-full" disabled={closing}>{closing ? "Cerrando..." : "Cerrar viaje"}</button>
            </form>
          </div>
        </div>
        <div className="space-y-4">
          {monthSections.map((month) => (
            <div className="card" key={month.key}>
              <div className="flex flex-col gap-3 mb-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="font-semibold">{month.label}</h2>
                  <p className="text-muted text-xs">{month.from && month.to ? `${month.from} a ${month.to}` : "Viajes cargados"}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-right text-xs sm:min-w-[460px]">
                  <div className="rounded-md border border-border bg-background/40 px-3 py-2">
                    <p className="text-muted">Precio venta</p>
                    <p className="font-semibold text-sm">{fmt(month.totals.sale_price)}</p>
                  </div>
                  <div className="rounded-md border border-border bg-background/40 px-3 py-2">
                    <p className="text-muted">Gastos</p>
                    <p className="font-semibold text-sm">{fmt(month.totals.expenses)}</p>
                  </div>
                  <div className="rounded-md border border-border bg-background/40 px-3 py-2">
                    <p className="text-muted">Profit</p>
                    <p className="font-semibold text-sm text-green-400">{fmt(month.totals.profit)}</p>
                  </div>
                </div>
                {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-muted text-xs">
                    <tr className="border-b border-border">
                      <th className="text-left py-2">Folio</th>
                      <th className="text-left py-2">Cliente</th>
                      <th className="text-left py-2">Ruta</th>
                      <th className="text-left py-2">Salida</th>
                      <th className="text-left py-2">Llegada</th>
                      <th className="text-left py-2">Operador</th>
                      <th className="text-left py-2">Unidad</th>
                      <th className="text-right py-2">Km</th>
                      <th className="text-right py-2">Precio venta</th>
                      <th className="text-right py-2">Gastos</th>
                      <th className="text-right py-2">Profit</th>
                      <th className="text-left py-2">Viaje</th>
                      <th className="text-left py-2">Pago</th>
                      <th className="text-right py-2">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {month.trips.map((trip: Trip) => {
                      const isEditing = editingFolio === trip.trip_folio;
                      return (
                      <tr key={trip.trip_folio} className="border-b border-border/50 align-top">
                        <td className="py-2 font-mono">{trip.trip_folio}</td>
                        <td className="py-2 min-w-28">
                          {isEditing ? <input className="input h-8 text-xs" value={editForm.customer || ""} onChange={(e) => setEditForm((f) => ({ ...f, customer: e.target.value }))} /> : (trip.customer || "-")}
                        </td>
                        <td className="py-2 min-w-44">
                          {isEditing ? (
                            <div className="grid gap-1">
                              <input className="input h-8 text-xs" value={editForm.origin || ""} onChange={(e) => setEditForm((f) => ({ ...f, origin: e.target.value }))} />
                              <input className="input h-8 text-xs" value={editForm.destination || ""} onChange={(e) => setEditForm((f) => ({ ...f, destination: e.target.value }))} />
                            </div>
                          ) : (
                            <span>{trip.origin || "-"} {"-"} {trip.destination || "-"}</span>
                          )}
                        </td>
                        <td className="py-2 min-w-28">
                          {isEditing ? <input type="date" className="input h-8 text-xs" value={editForm.departure_date || ""} onChange={(e) => setEditForm((f) => ({ ...f, departure_date: e.target.value }))} /> : (trip.departure_date || "-")}
                        </td>
                        <td className="py-2 min-w-28">
                          {isEditing ? <input type="date" className="input h-8 text-xs" value={editForm.arrival_date || ""} onChange={(e) => setEditForm((f) => ({ ...f, arrival_date: e.target.value }))} /> : (trip.arrival_date || "-")}
                        </td>
                        <td className="py-2 min-w-24">
                          {isEditing ? <input list="fleet-drivers" className="input h-8 text-xs" value={editForm.driver_key || ""} onChange={(e) => setEditForm((f) => ({ ...f, driver_key: e.target.value }))} /> : (trip.driver_key || <span className="text-yellow-300">pendiente</span>)}
                        </td>
                        <td className="py-2 min-w-24">
                          {isEditing ? <input list="fleet-units" className="input h-8 text-xs" value={editForm.unit_key || ""} onChange={(e) => setEditForm((f) => ({ ...f, unit_key: e.target.value }))} /> : (trip.unit_key || <span className="text-yellow-300">pendiente</span>)}
                        </td>
                        <td className="py-2 text-right min-w-20">
                          {isEditing ? <input type="number" className="input h-8 text-xs text-right" value={editForm.distance_km || ""} onChange={(e) => setEditForm((f) => ({ ...f, distance_km: e.target.value }))} /> : (trip.distance_km ?? "-")}
                        </td>
                        <td className="py-2 text-right min-w-28">
                          {isEditing ? <input type="number" className="input h-8 text-xs text-right" value={editForm.sale_price || ""} onChange={(e) => setEditForm((f) => ({ ...f, sale_price: e.target.value }))} /> : fmt(trip.sale_price || 0, trip.currency)}
                        </td>
                        <td className="py-2 text-right">{fmt(trip.expenses_total ?? trip.trip_cost ?? 0, trip.currency)}</td>
                        <td className="py-2 text-right">{fmt(trip.live_trip_profit ?? trip.trip_profit ?? 0, trip.currency)}</td>
                        <td className="py-2 min-w-28">
                          {isEditing ? (
                            <select className="input h-8 text-xs" value={editForm.trip_status || "active"} onChange={(e) => setEditForm((f) => ({ ...f, trip_status: e.target.value }))}>
                              <option value="active">Activo</option>
                              <option value="closed">Cerrado</option>
                              <option value="cancelled">Cancelado</option>
                            </select>
                          ) : (trip.trip_status || "active")}
                        </td>
                        <td className="py-2 min-w-28">{trip.payment_status || "receivable"}</td>
                        <td className="py-2">
                          {isEditing ? (
                            <div className="flex gap-2 justify-end">
                              <button type="button" className="btn-primary px-3 py-1 text-xs" disabled={savingEdit} onClick={() => saveEdit(trip.trip_folio || "")}>Guardar</button>
                              <button type="button" className="btn-ghost px-3 py-1 text-xs" disabled={savingEdit} onClick={() => setEditingFolio("")}>Cancelar</button>
                            </div>
                          ) : (
                            <div className="flex gap-2 justify-end">
                              <button type="button" className="btn-ghost px-2 py-1 text-xs" title="Editar viaje" disabled={savingEdit} onClick={() => startEdit(trip)}>Editar</button>
                              <button type="button" className="btn-ghost px-2 py-1 text-xs text-red-300" title="Borrar viaje" disabled={savingEdit} onClick={() => deleteTrip(trip)}>Borrar</button>
                            </div>
                          )}
                        </td>
                      </tr>
                      );
                    })}
                    {!month.trips.length && (
                      <tr><td colSpan={14} className="py-6 text-center text-muted">Sin viajes registrados en este mes.</td></tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-border text-xs font-semibold">
                      <td className="py-2" colSpan={8}>Total {month.label} ({month.totals.count} viajes)</td>
                      <td className="py-2 text-right">{fmt(month.totals.sale_price)}</td>
                      <td className="py-2 text-right">{fmt(month.totals.expenses)}</td>
                      <td className="py-2 text-right text-green-400">{fmt(month.totals.profit)}</td>
                      <td className="py-2" colSpan={3} />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          ))}
        </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}

      {lastTrip && (
        <div className="card mt-6">
          <h2 className="font-semibold mb-3">Ultimo viaje</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div><p className="text-muted text-xs">Folio</p><p className="font-mono">{lastTrip.trip_folio}</p></div>
            <div><p className="text-muted text-xs">Ruta</p><p>{lastTrip.origin} - {lastTrip.destination}</p></div>
            <div><p className="text-muted text-xs">Status</p><p>{lastTrip.trip_status} / {lastTrip.payment_status}</p></div>
            <div><p className="text-muted text-xs">Venta</p><p>{fmt(lastTrip.sale_price || 0, lastTrip.currency)}</p></div>
            <div><p className="text-muted text-xs">Costo</p><p>{fmt(lastTrip.trip_cost || 0, lastTrip.currency)}</p></div>
            <div><p className="text-muted text-xs">Profit</p><p className="text-green-400 font-semibold">{fmt(lastTrip.trip_profit || 0, lastTrip.currency)}</p></div>
          </div>
        </div>
      )}
    </div>
  );
}
