"use client";
import { useRef, useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

type Driver = {
  driver_key?: string;
  full_name?: string;
  phone?: string;
  license_number?: string;
  pay_scheme?: string;
  pay_rate?: number;
  status?: string;
};

type Unit = {
  unit_key?: string;
  plate?: string;
  brand?: string;
  model?: string;
  year?: number;
  unit_type?: string;
  odometer_km?: number;
  status?: string;
};

export default function AltaPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const { data: ops, loading: loadingOps, error: opsError } = useFleetOps(selectedCompanyId, ["drivers", "units"]);
  const [driverForm, setDriverForm] = useState({ driver_key: "", full_name: "", phone: "", license_number: "", pay_scheme: "commission", pay_rate: "", status: "active" });
  const [unitForm, setUnitForm] = useState({ unit_key: "", plate: "", brand: "", model: "", year: "", unit_type: "tractor", odometer_km: "", status: "active" });
  const [driverOverrides, setDriverOverrides] = useState<Record<string, Driver>>({});
  const [unitOverrides, setUnitOverrides] = useState<Record<string, Unit>>({});
  const [savingDriver, setSavingDriver] = useState(false);
  const [savingUnit, setSavingUnit] = useState(false);
  const [status, setStatus] = useState("");
  const [editingDriverKey, setEditingDriverKey] = useState<string | null>(null);
  const [editingUnitKey, setEditingUnitKey] = useState<string | null>(null);
  const [bajaDriverKey, setBajaDriverKey] = useState<string | null>(null);
  const [bajaUnitKey, setBajaUnitKey] = useState<string | null>(null);
  const driverFormRef = useRef<HTMLDivElement>(null);
  const unitFormRef = useRef<HTMLDivElement>(null);

  const drivers = mergeByKey((ops.drivers || []) as Driver[], driverOverrides, "driver_key");
  const units = mergeByKey((ops.units || []) as Unit[], unitOverrides, "unit_key");

  async function saveDriver(e: React.FormEvent) {
    e.preventDefault();
    setSavingDriver(true);
    setStatus("");
    try {
      const res = await fetch("/api/alta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "driver", empresa_id: selectedCompanyId, ...driverForm }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al guardar chofer"); return; }
      const driver = data.data?.driver || {};
      setDriverOverrides((current) => ({ ...current, [driver.driver_key]: driver }));
      setDriverForm({ driver_key: "", full_name: "", phone: "", license_number: "", pay_scheme: "commission", pay_rate: "", status: "active" });
      setEditingDriverKey(null);
      setStatus(`Chofer ${driver.driver_key} guardado.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingDriver(false);
    }
  }

  async function saveUnit(e: React.FormEvent) {
    e.preventDefault();
    setSavingUnit(true);
    setStatus("");
    try {
      const res = await fetch("/api/alta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "unit", empresa_id: selectedCompanyId, ...unitForm }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al guardar unidad"); return; }
      const unit = data.data?.unit || {};
      setUnitOverrides((current) => ({ ...current, [unit.unit_key]: unit }));
      setUnitForm({ unit_key: "", plate: "", brand: "", model: "", year: "", unit_type: "tractor", odometer_km: "", status: "active" });
      setEditingUnitKey(null);
      setStatus(`Unidad ${unit.unit_key} guardada.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingUnit(false);
    }
  }

  function startEditDriver(driver: Driver) {
    setDriverForm({
      driver_key: driver.driver_key || "",
      full_name: driver.full_name || "",
      phone: driver.phone || "",
      license_number: driver.license_number || "",
      pay_scheme: driver.pay_scheme || "commission",
      pay_rate: String(driver.pay_rate ?? ""),
      status: driver.status || "active",
    });
    setEditingDriverKey(driver.driver_key || null);
    setStatus("");
    driverFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function cancelEditDriver() {
    setDriverForm({ driver_key: "", full_name: "", phone: "", license_number: "", pay_scheme: "commission", pay_rate: "", status: "active" });
    setEditingDriverKey(null);
  }

  function startEditUnit(unit: Unit) {
    setUnitForm({
      unit_key: unit.unit_key || "",
      plate: unit.plate || "",
      brand: unit.brand || "",
      model: unit.model || "",
      year: String(unit.year ?? ""),
      unit_type: unit.unit_type || "tractor",
      odometer_km: String(unit.odometer_km ?? ""),
      status: unit.status || "active",
    });
    setEditingUnitKey(unit.unit_key || null);
    setStatus("");
    unitFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function cancelEditUnit() {
    setUnitForm({ unit_key: "", plate: "", brand: "", model: "", year: "", unit_type: "tractor", odometer_km: "", status: "active" });
    setEditingUnitKey(null);
  }

  async function bajaDriver(driver: Driver) {
    if (!driver.driver_key) return;
    if (!confirm(`¿Dar de baja al chofer ${driver.full_name || driver.driver_key}? Su historial se conserva, pero ya no aparecerá disponible para nuevas operaciones.`)) return;
    setBajaDriverKey(driver.driver_key);
    setStatus("");
    try {
      const res = await fetch("/api/alta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "driver", empresa_id: selectedCompanyId, driver_key: driver.driver_key, baja: true }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al dar de baja"); return; }
      const updated = data.data?.driver || { ...driver, status: "inactive" };
      setDriverOverrides((current) => ({ ...current, [driver.driver_key as string]: { ...driver, ...updated } }));
      setStatus(`Chofer ${driver.driver_key} dado de baja.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setBajaDriverKey(null);
    }
  }

  async function bajaUnit(unit: Unit) {
    if (!unit.unit_key) return;
    if (!confirm(`¿Dar de baja la unidad ${unit.plate || unit.unit_key}? Su historial se conserva, pero ya no aparecerá disponible para nuevas operaciones.`)) return;
    setBajaUnitKey(unit.unit_key);
    setStatus("");
    try {
      const res = await fetch("/api/alta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "unit", empresa_id: selectedCompanyId, unit_key: unit.unit_key, baja: true }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al dar de baja"); return; }
      const updated = data.data?.unit || { ...unit, status: "inactive" };
      setUnitOverrides((current) => ({ ...current, [unit.unit_key as string]: { ...unit, ...updated } }));
      setStatus(`Unidad ${unit.unit_key} dada de baja.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setBajaUnitKey(null);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Alta</h1>
      <p className="text-muted text-sm mb-6">Captura choferes y unidades antes de operar viajes, combustible o mantenimiento</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <div className="space-y-4">
          {opsError && <div className="card border-red-800 bg-red-900/20 text-red-300 text-sm">{opsError}</div>}
          <div className="grid gap-4 lg:grid-cols-2">
            <div className={`card ${editingDriverKey ? "ring-2 ring-primary" : ""}`} ref={driverFormRef}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold">{editingDriverKey ? `Editando chofer ${editingDriverKey}` : "Alta de chofer"}</h2>
                {editingDriverKey && <button type="button" onClick={cancelEditDriver} className="text-xs text-muted hover:text-fg">Cancelar edición</button>}
              </div>
              <form onSubmit={saveDriver} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Clave chofer</label><input className="input" value={driverForm.driver_key} onChange={(e) => setDriverForm((f) => ({ ...f, driver_key: e.target.value.trim().toUpperCase() }))} placeholder="DRV-001" required disabled={!!editingDriverKey} /></div>
                  <div><label className="label">Nombre</label><input className="input" value={driverForm.full_name} onChange={(e) => setDriverForm((f) => ({ ...f, full_name: e.target.value }))} required /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Telefono</label><input className="input" value={driverForm.phone} onChange={(e) => setDriverForm((f) => ({ ...f, phone: e.target.value }))} /></div>
                  <div><label className="label">Licencia</label><input className="input" value={driverForm.license_number} onChange={(e) => setDriverForm((f) => ({ ...f, license_number: e.target.value }))} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="label">Pago</label>
                    <select className="input" value={driverForm.pay_scheme} onChange={(e) => setDriverForm((f) => ({ ...f, pay_scheme: e.target.value }))}>
                      <option value="commission">Comision</option>
                      <option value="fixed">Fijo</option>
                      <option value="per_trip">Por viaje</option>
                    </select>
                  </div>
                  <div><label className="label">Tarifa</label><input type="number" className="input" value={driverForm.pay_rate} onChange={(e) => setDriverForm((f) => ({ ...f, pay_rate: e.target.value }))} /></div>
                  <div>
                    <label className="label">Status</label>
                    <select className="input" value={driverForm.status} onChange={(e) => setDriverForm((f) => ({ ...f, status: e.target.value }))}>
                      <option value="active">Activo</option>
                      <option value="inactive">Inactivo</option>
                    </select>
                  </div>
                </div>
                <button type="submit" className="btn-primary w-full" disabled={savingDriver}>{savingDriver ? "Guardando..." : editingDriverKey ? "Actualizar chofer" : "Guardar chofer"}</button>
              </form>
            </div>

            <div className={`card ${editingUnitKey ? "ring-2 ring-primary" : ""}`} ref={unitFormRef}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold">{editingUnitKey ? `Editando unidad ${editingUnitKey}` : "Alta de unidad"}</h2>
                {editingUnitKey && <button type="button" onClick={cancelEditUnit} className="text-xs text-muted hover:text-fg">Cancelar edición</button>}
              </div>
              <form onSubmit={saveUnit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Clave unidad</label><input className="input" value={unitForm.unit_key} onChange={(e) => setUnitForm((f) => ({ ...f, unit_key: e.target.value.trim().toUpperCase() }))} placeholder="TR-001" required disabled={!!editingUnitKey} /></div>
                  <div><label className="label">Placas</label><input className="input" value={unitForm.plate} onChange={(e) => setUnitForm((f) => ({ ...f, plate: e.target.value.toUpperCase() }))} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Marca</label><input className="input" value={unitForm.brand} onChange={(e) => setUnitForm((f) => ({ ...f, brand: e.target.value }))} /></div>
                  <div><label className="label">Modelo</label><input className="input" value={unitForm.model} onChange={(e) => setUnitForm((f) => ({ ...f, model: e.target.value }))} /></div>
                  <div><label className="label">Anio</label><input type="number" className="input" value={unitForm.year} onChange={(e) => setUnitForm((f) => ({ ...f, year: e.target.value }))} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="label">Tipo</label>
                    <select className="input" value={unitForm.unit_type} onChange={(e) => setUnitForm((f) => ({ ...f, unit_type: e.target.value }))}>
                      <option value="tractor">Tractor</option>
                      <option value="trailer">Remolque</option>
                      <option value="box">Caja</option>
                      <option value="pickup">Pickup</option>
                    </select>
                  </div>
                  <div><label className="label">Odometro km</label><input type="number" className="input" value={unitForm.odometer_km} onChange={(e) => setUnitForm((f) => ({ ...f, odometer_km: e.target.value }))} /></div>
                  <div>
                    <label className="label">Status</label>
                    <select className="input" value={unitForm.status} onChange={(e) => setUnitForm((f) => ({ ...f, status: e.target.value }))}>
                      <option value="active">Activo</option>
                      <option value="maintenance">Mantenimiento</option>
                      <option value="inactive">Inactivo</option>
                    </select>
                  </div>
                </div>
                <button type="submit" className="btn-primary w-full" disabled={savingUnit}>{savingUnit ? "Guardando..." : editingUnitKey ? "Actualizar unidad" : "Guardar unidad"}</button>
              </form>
            </div>
          </div>

          {status && <p className="text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">Choferes dados de alta</h2>
                {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-muted text-xs">
                    <tr className="border-b border-border">
                      <th className="text-left py-2">Clave</th>
                      <th className="text-left py-2">Nombre</th>
                      <th className="text-left py-2">Telefono</th>
                      <th className="text-left py-2">Licencia</th>
                      <th className="text-left py-2">Pago</th>
                      <th className="text-right py-2">Tarifa</th>
                      <th className="text-left py-2">Status</th>
                      <th className="text-right py-2">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drivers.map((driver) => (
                      <tr key={driver.driver_key} className={`border-b border-border/50 ${driver.status === "inactive" ? "opacity-50" : ""}`}>
                        <td className="py-2 font-mono">{driver.driver_key}</td>
                        <td className="py-2">{driver.full_name || "-"}</td>
                        <td className="py-2">{driver.phone || "-"}</td>
                        <td className="py-2">{driver.license_number || "-"}</td>
                        <td className="py-2">{driver.pay_scheme || "-"}</td>
                        <td className="py-2 text-right">{Number(driver.pay_rate || 0).toLocaleString("es-MX")}</td>
                        <td className="py-2">{driver.status === "inactive" ? "Dado de baja" : "Activo"}</td>
                        <td className="py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button type="button" title="Editar" onClick={() => startEditDriver(driver)} className="text-muted hover:text-fg">✎</button>
                            {driver.status !== "inactive" && (
                              <button type="button" title="Dar de baja" onClick={() => bajaDriver(driver)} disabled={bajaDriverKey === driver.driver_key} className="text-muted hover:text-red-400 disabled:opacity-50">🗑</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!drivers.length && <tr><td colSpan={8} className="py-6 text-center text-muted">Sin choferes registrados.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">Unidades dadas de alta</h2>
                {loadingOps && <span className="text-muted text-xs">Cargando...</span>}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-muted text-xs">
                    <tr className="border-b border-border">
                      <th className="text-left py-2">Clave</th>
                      <th className="text-left py-2">Placas</th>
                      <th className="text-left py-2">Marca</th>
                      <th className="text-left py-2">Modelo</th>
                      <th className="text-right py-2">Anio</th>
                      <th className="text-left py-2">Tipo</th>
                      <th className="text-right py-2">Km</th>
                      <th className="text-left py-2">Status</th>
                      <th className="text-right py-2">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {units.map((unit) => (
                      <tr key={unit.unit_key} className={`border-b border-border/50 ${unit.status === "inactive" ? "opacity-50" : ""}`}>
                        <td className="py-2 font-mono">{unit.unit_key}</td>
                        <td className="py-2">{unit.plate || "-"}</td>
                        <td className="py-2">{unit.brand || "-"}</td>
                        <td className="py-2">{unit.model || "-"}</td>
                        <td className="py-2 text-right">{unit.year || "-"}</td>
                        <td className="py-2">{unit.unit_type || "-"}</td>
                        <td className="py-2 text-right">{Number(unit.odometer_km || 0).toLocaleString("es-MX")}</td>
                        <td className="py-2">{unit.status === "inactive" ? "Dado de baja" : unit.status === "maintenance" ? "Mantenimiento" : "Activo"}</td>
                        <td className="py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button type="button" title="Editar" onClick={() => startEditUnit(unit)} className="text-muted hover:text-fg">✎</button>
                            {unit.status !== "inactive" && (
                              <button type="button" title="Dar de baja" onClick={() => bajaUnit(unit)} disabled={bajaUnitKey === unit.unit_key} className="text-muted hover:text-red-400 disabled:opacity-50">🗑</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!units.length && <tr><td colSpan={9} className="py-6 text-center text-muted">Sin unidades registradas.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function mergeByKey<T extends Record<string, any>>(rows: T[], overrides: Record<string, T>, key: string): T[] {
  const byKey = new Map<string, T>();
  rows.forEach((row) => {
    const id = String(row[key] || "");
    if (id) byKey.set(id, row);
  });
  Object.entries(overrides).forEach(([id, row]) => {
    if (id) byKey.set(id, row);
  });
  return Array.from(byKey.values());
}
