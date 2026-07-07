"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

type Trip = {
  trip_folio?: string;
  customer?: string;
  origin?: string;
  destination?: string;
  sale_price?: number;
  currency?: string;
  trip_cost?: number;
  trip_profit?: number;
  trip_status?: string;
  payment_status?: string;
};

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function ViajesPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps, error: opsError } = useFleetOps(selectedCompanyId, ["trips", "drivers", "units"]);
  const [form, setForm] = useState({ customer: "", origin: "", destination: "", sale_price: "", departure_date: "", driver_key: "", unit_key: "", distance_km: "" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastTrip, setLastTrip] = useState<Trip | null>(null);
  const [closeFolio, setCloseFolio] = useState("");
  const [closing, setClosing] = useState(false);

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
      setStatus(`Viaje ${data.data?.trip?.trip_folio} creado.`);
      setForm({ customer: "", origin: "", destination: "", sale_price: "", departure_date: "", driver_key: "", unit_key: "", distance_km: "" });
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
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Viajes recientes</h2>
            {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-muted text-xs">
                <tr className="border-b border-border">
                  <th className="text-left py-2">Folio</th>
                  <th className="text-left py-2">Cliente</th>
                  <th className="text-left py-2">Ruta</th>
                  <th className="text-left py-2">Operador</th>
                  <th className="text-left py-2">Unidad</th>
                  <th className="text-right py-2">Profit</th>
                </tr>
              </thead>
              <tbody>
                {(ops.trips || []).slice(0, 10).map((trip: any) => (
                  <tr key={trip.trip_folio} className="border-b border-border/50">
                    <td className="py-2 font-mono">{trip.trip_folio}</td>
                    <td className="py-2">{trip.customer || "-"}</td>
                    <td className="py-2">{trip.origin || "-"} {"-"} {trip.destination || "-"}</td>
                    <td className="py-2">{trip.driver_key || <span className="text-yellow-300">pendiente</span>}</td>
                    <td className="py-2">{trip.unit_key || <span className="text-yellow-300">pendiente</span>}</td>
                    <td className="py-2 text-right">{fmt(trip.trip_profit || 0, trip.currency)}</td>
                  </tr>
                ))}
                {!(ops.trips || []).length && (
                  <tr><td colSpan={6} className="py-6 text-center text-muted">Sin viajes registrados.</td></tr>
                )}
              </tbody>
            </table>
          </div>
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
