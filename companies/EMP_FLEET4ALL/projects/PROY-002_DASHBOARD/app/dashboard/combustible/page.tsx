"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function CombustiblePage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const ops = useFleetOps(selectedCompanyId, ["trips", "drivers", "units", "fuel_loads", "fuel_efficiency"]);
  const [form, setForm] = useState({ unit_key: "", driver_key: "", trip_folio: "", liters: "", amount: "", load_date: "", odometer_km: "", station: "", as_expense: true });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastLoad, setLastLoad] = useState<any>(null);

  const [mileageForm, setMileageForm] = useState({ unit_key: "", from: "", to: "" });
  const [efficiency, setEfficiency] = useState<any>(null);
  const [calculating, setCalculating] = useState(false);
  const [unitForm, setUnitForm] = useState({ unit_key: "", plate: "", brand: "", model: "", year: "", unit_type: "tractor", odometer_km: "" });
  const [savingUnit, setSavingUnit] = useState(false);
  const [createdUnits, setCreatedUnits] = useState<any[]>([]);

  const units = [...(ops.data?.units || []), ...createdUnits.filter((created) => !(ops.data?.units || []).some((unit: any) => unit.unit_key === created.unit_key))];
  const drivers = ops.data?.drivers || [];
  const trips = ops.data?.trips || [];
  const fuelLoads = ops.data?.fuel_loads || [];
  const efficiencyRows = ops.data?.fuel_efficiency || [];

  async function handleCapture(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("");
    try {
      const res = await fetch("/api/combustible", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "load", empresa_id: selectedCompanyId, ...form, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al capturar carga"); return; }
      setLastLoad(data.data?.fuel_load || null);
      setStatus(`Carga ${data.data?.fuel_load?.fuel_folio} registrada.${data.data?.warnings?.length ? " (" + data.data.warnings.join("; ") + ")" : ""}`);
      setForm({ unit_key: "", driver_key: "", trip_folio: "", liters: "", amount: "", load_date: "", odometer_km: "", station: "", as_expense: true });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function handleMileage(e: React.FormEvent) {
    e.preventDefault();
    setCalculating(true);
    setStatus("");
    try {
      const res = await fetch("/api/combustible", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "mileage", empresa_id: selectedCompanyId, unit_key: mileageForm.unit_key, period: { from: mileageForm.from, to: mileageForm.to }, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al calcular rendimiento"); return; }
      setEfficiency(data.data?.efficiency || null);
      setStatus("Rendimiento calculado.");
    } catch {
      setStatus("Error de conexion");
    } finally {
      setCalculating(false);
    }
  }

  async function handleUnit(e: React.FormEvent) {
    e.preventDefault();
    setSavingUnit(true);
    setStatus("");
    try {
      const res = await fetch("/api/combustible", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "unit", empresa_id: selectedCompanyId, ...unitForm }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al guardar unidad"); return; }
      const unit = data.data?.unit;
      if (unit) {
        setCreatedUnits((rows) => [unit, ...rows.filter((row) => row.unit_key !== unit.unit_key)]);
        setForm((f) => ({ ...f, unit_key: unit.unit_key, odometer_km: unit.odometer_km ? String(unit.odometer_km) : f.odometer_km }));
        setMileageForm((f) => ({ ...f, unit_key: unit.unit_key }));
      }
      setUnitForm({ unit_key: "", plate: "", brand: "", model: "", year: "", unit_type: "tractor", odometer_km: "" });
      setStatus(`Unidad ${unit?.unit_key || ""} guardada.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingUnit(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Combustible</h1>
      <p className="text-muted text-sm mb-6">Cargas de combustible y rendimiento por unidad</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <>
          <datalist id="fuel-units">{units.map((unit: any) => <option key={unit.unit_key} value={unit.unit_key}>{unit.plate || unit.unit_key}</option>)}</datalist>
          <datalist id="fuel-drivers">{drivers.map((driver: any) => <option key={driver.driver_key} value={driver.driver_key}>{driver.full_name}</option>)}</datalist>
          <datalist id="fuel-trips">{trips.map((trip: any) => <option key={trip.trip_folio} value={trip.trip_folio}>{trip.origin} - {trip.destination}</option>)}</datalist>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card">
              <h2 className="font-semibold mb-4">Alta rapida de unidad</h2>
              <form onSubmit={handleUnit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Clave unidad</label><input className="input" placeholder="TR-01" value={unitForm.unit_key} onChange={(e) => setUnitForm((f) => ({ ...f, unit_key: e.target.value.toUpperCase() }))} required /></div>
                  <div><label className="label">Placas</label><input className="input" value={unitForm.plate} onChange={(e) => setUnitForm((f) => ({ ...f, plate: e.target.value.toUpperCase() }))} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Marca</label><input className="input" value={unitForm.brand} onChange={(e) => setUnitForm((f) => ({ ...f, brand: e.target.value }))} /></div>
                  <div><label className="label">Modelo</label><input className="input" value={unitForm.model} onChange={(e) => setUnitForm((f) => ({ ...f, model: e.target.value }))} /></div>
                  <div><label className="label">Año</label><input type="number" className="input" value={unitForm.year} onChange={(e) => setUnitForm((f) => ({ ...f, year: e.target.value }))} /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Tipo</label>
                    <select className="input" value={unitForm.unit_type} onChange={(e) => setUnitForm((f) => ({ ...f, unit_type: e.target.value }))}>
                      <option value="tractor">Tractor</option>
                      <option value="trailer">Remolque</option>
                      <option value="van">Van</option>
                      <option value="pickup">Pickup</option>
                    </select>
                  </div>
                  <div><label className="label">Odometro actual</label><input type="number" className="input" value={unitForm.odometer_km} onChange={(e) => setUnitForm((f) => ({ ...f, odometer_km: e.target.value }))} /></div>
                </div>
                <button type="submit" className="btn-ghost w-full" disabled={savingUnit}>{savingUnit ? "Guardando..." : "Guardar unidad"}</button>
              </form>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Registrar carga</h2>
              <form onSubmit={handleCapture} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Unidad</label><input className="input" list="fuel-units" value={form.unit_key} onChange={(e) => setForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
                  <div><label className="label">Operador</label><input className="input" list="fuel-drivers" value={form.driver_key} onChange={(e) => setForm((f) => ({ ...f, driver_key: e.target.value }))} /></div>
                </div>
                <div><label className="label">Viaje asociado</label><input className="input font-mono" list="fuel-trips" value={form.trip_folio} onChange={(e) => setForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Litros</label><input type="number" className="input" value={form.liters} onChange={(e) => setForm((f) => ({ ...f, liters: e.target.value }))} required /></div>
                  <div><label className="label">Monto</label><input type="number" className="input" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Fecha</label><input type="date" className="input" value={form.load_date} onChange={(e) => setForm((f) => ({ ...f, load_date: e.target.value }))} /></div>
                  <div><label className="label">Odometro km</label><input type="number" className="input" value={form.odometer_km} onChange={(e) => setForm((f) => ({ ...f, odometer_km: e.target.value }))} /></div>
                </div>
                <div><label className="label">Estacion</label><input className="input" value={form.station} onChange={(e) => setForm((f) => ({ ...f, station: e.target.value }))} /></div>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.as_expense} onChange={(e) => setForm((f) => ({ ...f, as_expense: e.target.checked }))} /> Registrar tambien como gasto del viaje</label>
                <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Guardando..." : "Registrar carga"}</button>
              </form>
              {lastLoad && (
                <div className="mt-4 pt-4 border-t border-border text-sm">
                  <p><span className="text-muted">Precio/litro:</span> {Number(lastLoad.price_per_liter || 0).toFixed(3)}</p>
                </div>
              )}
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Rendimiento por periodo</h2>
              <form onSubmit={handleMileage} className="space-y-3">
                <div><label className="label">Unidad</label><input className="input" list="fuel-units" value={mileageForm.unit_key} onChange={(e) => setMileageForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Desde</label><input type="date" className="input" value={mileageForm.from} onChange={(e) => setMileageForm((f) => ({ ...f, from: e.target.value }))} required /></div>
                  <div><label className="label">Hasta</label><input type="date" className="input" value={mileageForm.to} onChange={(e) => setMileageForm((f) => ({ ...f, to: e.target.value }))} required /></div>
                </div>
                <button type="submit" className="btn-ghost w-full" disabled={calculating}>{calculating ? "Calculando..." : "Calcular rendimiento"}</button>
              </form>
              {efficiency && (
                <div className="mt-4 pt-4 border-t border-border text-sm space-y-1">
                  <p><span className="text-muted">km/litro:</span> {efficiency.km_per_liter}</p>
                  <p><span className="text-muted">Esperado:</span> {efficiency.expected_km_per_liter ?? "-"}</p>
                  <p><span className="text-muted">Desviacion:</span> {efficiency.deviation_pct ?? "-"}%</p>
                  <p><span className="text-muted">Flag:</span> <span className={efficiency.flag === "alert" ? "badge-red" : efficiency.flag === "warning" ? "badge-yellow" : "badge-green"}>{efficiency.flag}</span></p>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2 mt-4">
            <div className="card">
              <h2 className="font-semibold mb-4">Ultimas cargas</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-muted"><tr><th className="text-left py-2">Folio</th><th className="text-left py-2">Unidad</th><th className="text-left py-2">Litros</th><th className="text-left py-2">Monto</th></tr></thead>
                  <tbody>
                    {fuelLoads.map((load: any) => (
                      <tr key={load.fuel_folio} className="border-t border-border">
                        <td className="py-2 font-mono">{load.fuel_folio}</td>
                        <td className="py-2">{load.unit_key}</td>
                        <td className="py-2">{load.liters}</td>
                        <td className="py-2">{fmt(load.amount, load.currency)}</td>
                      </tr>
                    ))}
                    {!fuelLoads.length && <tr><td className="py-4 text-muted" colSpan={4}>{ops.loading ? "Cargando..." : "Sin cargas."}</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Alertas de rendimiento</h2>
              <div className="space-y-2 text-sm">
                {efficiencyRows.map((row: any) => (
                  <div key={`${row.unit_key}-${row.period_to}`} className="flex items-center justify-between border-t border-border pt-2">
                    <span>{row.unit_key} - {row.km_per_liter} km/l</span>
                    <span className={row.flag === "alert" ? "badge-red" : row.flag === "warning" ? "badge-yellow" : "badge-green"}>{row.flag}</span>
                  </div>
                ))}
                {!efficiencyRows.length && <p className="text-muted">{ops.loading ? "Cargando..." : "Sin calculos de rendimiento."}</p>}
              </div>
            </div>
          </div>
        </>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
