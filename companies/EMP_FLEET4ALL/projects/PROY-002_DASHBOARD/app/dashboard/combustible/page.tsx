"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";

export default function CombustiblePage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const [form, setForm] = useState({ unit_key: "", liters: "", amount: "", load_date: "", odometer_km: "", station: "" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [lastLoad, setLastLoad] = useState<any>(null);

  const [mileageForm, setMileageForm] = useState({ unit_key: "", from: "", to: "" });
  const [efficiency, setEfficiency] = useState<any>(null);
  const [calculating, setCalculating] = useState(false);

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
      setForm({ unit_key: "", liters: "", amount: "", load_date: "", odometer_km: "", station: "" });
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
    } catch {
      setStatus("Error de conexion");
    } finally {
      setCalculating(false);
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
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold mb-4">Registrar carga</h2>
            <form onSubmit={handleCapture} className="space-y-3">
              <div><label className="label">Unidad</label><input className="input" value={form.unit_key} onChange={(e) => setForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Litros</label><input type="number" className="input" value={form.liters} onChange={(e) => setForm((f) => ({ ...f, liters: e.target.value }))} required /></div>
                <div><label className="label">Monto</label><input type="number" className="input" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Fecha</label><input type="date" className="input" value={form.load_date} onChange={(e) => setForm((f) => ({ ...f, load_date: e.target.value }))} /></div>
                <div><label className="label">Odometro km</label><input type="number" className="input" value={form.odometer_km} onChange={(e) => setForm((f) => ({ ...f, odometer_km: e.target.value }))} /></div>
              </div>
              <div><label className="label">Estacion (opcional)</label><input className="input" value={form.station} onChange={(e) => setForm((f) => ({ ...f, station: e.target.value }))} /></div>
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
              <div><label className="label">Unidad</label><input className="input" value={mileageForm.unit_key} onChange={(e) => setMileageForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
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
                <p>
                  <span className="text-muted">Flag:</span>{" "}
                  <span className={efficiency.flag === "alert" ? "badge-red" : efficiency.flag === "warning" ? "badge-yellow" : "badge-green"}>{efficiency.flag}</span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
