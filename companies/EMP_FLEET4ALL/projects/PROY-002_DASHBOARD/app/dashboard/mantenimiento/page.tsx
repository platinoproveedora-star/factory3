"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";

export default function MantenimientoPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const [planForm, setPlanForm] = useState({ unit_key: "", service_type: "", every_km: "", every_days: "" });
  const [savingPlan, setSavingPlan] = useState(false);

  const [svcForm, setSvcForm] = useState({ unit_key: "", plan_folio: "", service_date: "", odometer_km: "", service_type: "", cost: "" });
  const [savingSvc, setSavingSvc] = useState(false);

  const [kardexForm, setKardexForm] = useState({ part_key: "", movement_type: "in", quantity: "", unit_cost: "" });
  const [savingKardex, setSavingKardex] = useState(false);

  const [recordUnit, setRecordUnit] = useState("");
  const [record, setRecord] = useState<any>(null);
  const [loadingRecord, setLoadingRecord] = useState(false);

  const [status, setStatus] = useState("");

  async function handlePlan(e: React.FormEvent) {
    e.preventDefault();
    setSavingPlan(true);
    setStatus("");
    try {
      const res = await fetch("/api/mantenimiento", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "plan", empresa_id: selectedCompanyId, ...planForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al crear plan"); return; }
      setStatus(`Plan ${data.data?.maintenance_plan?.plan_folio} creado. Proximo: ${data.data?.maintenance_plan?.next_due_km ?? "-"} km`);
      setPlanForm({ unit_key: "", service_type: "", every_km: "", every_days: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingPlan(false);
    }
  }

  async function handleService(e: React.FormEvent) {
    e.preventDefault();
    setSavingSvc(true);
    setStatus("");
    try {
      const res = await fetch("/api/mantenimiento", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "service", empresa_id: selectedCompanyId, ...svcForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al registrar servicio"); return; }
      setStatus(`Servicio ${data.data?.service?.service_folio} registrado.`);
      setSvcForm({ unit_key: "", plan_folio: "", service_date: "", odometer_km: "", service_type: "", cost: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingSvc(false);
    }
  }

  async function handleKardex(e: React.FormEvent) {
    e.preventDefault();
    setSavingKardex(true);
    setStatus("");
    try {
      const res = await fetch("/api/mantenimiento", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "kardex", empresa_id: selectedCompanyId, ...kardexForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error en movimiento de refaccion"); return; }
      setStatus(`Movimiento ${data.data?.movement?.movement_folio} registrado.${data.data?.warnings?.length ? " (" + data.data.warnings.join("; ") + ")" : ""}`);
      setKardexForm({ part_key: "", movement_type: "in", quantity: "", unit_cost: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingKardex(false);
    }
  }

  async function handleRecord(e: React.FormEvent) {
    e.preventDefault();
    setLoadingRecord(true);
    setRecord(null);
    try {
      const res = await fetch(`/api/mantenimiento?empresa_id=${encodeURIComponent(selectedCompanyId)}&unit_key=${encodeURIComponent(recordUnit)}`);
      const data = await res.json();
      if (data.ok) setRecord(data.data);
      else setStatus(data.error || "Error al consultar expediente");
    } catch {
      setStatus("Error de conexion");
    } finally {
      setLoadingRecord(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Mantenimiento</h1>
      <p className="text-muted text-sm mb-6">Planes, servicios, refacciones y expediente de unidad</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold mb-4">Nuevo plan</h2>
            <form onSubmit={handlePlan} className="space-y-3">
              <div><label className="label">Unidad</label><input className="input" value={planForm.unit_key} onChange={(e) => setPlanForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
              <div><label className="label">Tipo de servicio</label><input className="input" placeholder="oil, brakes, tires..." value={planForm.service_type} onChange={(e) => setPlanForm((f) => ({ ...f, service_type: e.target.value }))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Cada km</label><input type="number" className="input" value={planForm.every_km} onChange={(e) => setPlanForm((f) => ({ ...f, every_km: e.target.value }))} /></div>
                <div><label className="label">Cada dias</label><input type="number" className="input" value={planForm.every_days} onChange={(e) => setPlanForm((f) => ({ ...f, every_days: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn-primary w-full" disabled={savingPlan}>{savingPlan ? "Guardando..." : "Crear plan"}</button>
            </form>
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Registrar servicio</h2>
            <form onSubmit={handleService} className="space-y-3">
              <div><label className="label">Unidad</label><input className="input" value={svcForm.unit_key} onChange={(e) => setSvcForm((f) => ({ ...f, unit_key: e.target.value }))} required /></div>
              <div><label className="label">Folio del plan (opcional)</label><input className="input font-mono" placeholder="M-0001" value={svcForm.plan_folio} onChange={(e) => setSvcForm((f) => ({ ...f, plan_folio: e.target.value.toUpperCase() }))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Fecha</label><input type="date" className="input" value={svcForm.service_date} onChange={(e) => setSvcForm((f) => ({ ...f, service_date: e.target.value }))} /></div>
                <div><label className="label">Odometro km</label><input type="number" className="input" value={svcForm.odometer_km} onChange={(e) => setSvcForm((f) => ({ ...f, odometer_km: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Tipo</label><input className="input" value={svcForm.service_type} onChange={(e) => setSvcForm((f) => ({ ...f, service_type: e.target.value }))} required /></div>
                <div><label className="label">Costo</label><input type="number" className="input" value={svcForm.cost} onChange={(e) => setSvcForm((f) => ({ ...f, cost: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn-primary w-full" disabled={savingSvc}>{savingSvc ? "Guardando..." : "Registrar servicio"}</button>
            </form>
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Kardex de refacciones</h2>
            <form onSubmit={handleKardex} className="space-y-3">
              <div><label className="label">Refaccion (part_key)</label><input className="input" value={kardexForm.part_key} onChange={(e) => setKardexForm((f) => ({ ...f, part_key: e.target.value }))} required /></div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label">Movimiento</label>
                  <select className="input" value={kardexForm.movement_type} onChange={(e) => setKardexForm((f) => ({ ...f, movement_type: e.target.value }))}>
                    <option value="in">Entrada</option>
                    <option value="out">Salida</option>
                  </select>
                </div>
                <div><label className="label">Cantidad</label><input type="number" className="input" value={kardexForm.quantity} onChange={(e) => setKardexForm((f) => ({ ...f, quantity: e.target.value }))} required /></div>
                <div><label className="label">Costo unit.</label><input type="number" className="input" value={kardexForm.unit_cost} onChange={(e) => setKardexForm((f) => ({ ...f, unit_cost: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn-ghost w-full" disabled={savingKardex}>{savingKardex ? "Guardando..." : "Registrar movimiento"}</button>
            </form>
          </div>

          <div className="card">
            <h2 className="font-semibold mb-4">Expediente de unidad</h2>
            <form onSubmit={handleRecord} className="space-y-3">
              <div><label className="label">Unidad</label><input className="input" value={recordUnit} onChange={(e) => setRecordUnit(e.target.value)} required /></div>
              <button type="submit" className="btn-ghost w-full" disabled={loadingRecord}>{loadingRecord ? "Buscando..." : "Consultar expediente"}</button>
            </form>
            {record && (
              <div className="mt-4 pt-4 border-t border-border text-sm space-y-2">
                <p><span className="text-muted">Odometro:</span> {record.unit?.odometer_km} km</p>
                <p><span className="text-muted">Servicios:</span> {record.service_history?.length || 0}</p>
                <p><span className="text-muted">Planes activos:</span> {record.active_plans?.length || 0}</p>
                <p><span className="text-muted">Costo mantenimiento:</span> {Number(record.maintenance_cost_period?.total || 0).toLocaleString("es-MX", { style: "currency", currency: record.maintenance_cost_period?.currency || "MXN" })}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
