"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

export default function CartaPortePage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const ops = useFleetOps(selectedCompanyId, ["trips", "cartaporte_stamps"]);
  const [form, setForm] = useState({ trip_folio: "", cfdi_type: "traslado", descripcion: "", cantidad: "", peso_kg: "", clave_prod_serv: "" });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [draft, setDraft] = useState<any>(null);
  const [validated, setValidated] = useState(false);
  const [stampFolio, setStampFolio] = useState("");
  const [rfc, setRfc] = useState("");
  const [stamping, setStamping] = useState(false);
  const [validating, setValidating] = useState(false);

  const trips = ops.data?.trips || [];
  const stamps = ops.data?.cartaporte_stamps || [];

  async function handleBuild(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("");
    setDraft(null);
    setValidated(false);
    try {
      const res = await fetch("/api/cartaporte", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "build",
          empresa_id: selectedCompanyId,
          trip_folio: form.trip_folio,
          cfdi_type: form.cfdi_type,
          mercancias: [{ descripcion: form.descripcion, cantidad: Number(form.cantidad), peso_kg: Number(form.peso_kg), clave_prod_serv: form.clave_prod_serv }],
          dry_run: false,
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        const missing = data.data?.missing;
        setStatus(missing ? `Faltan campos: ${missing.join(", ")}` : (data.error || "Error al armar draft"));
        return;
      }
      setDraft(data.data?.cartaporte || null);
      setStampFolio(data.data?.cartaporte?.stamp_folio || "");
      setStatus(`Draft ${data.data?.cartaporte?.stamp_folio} creado.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    if (!draft) return;
    setValidating(true);
    setStatus("");
    setValidated(false);
    try {
      const res = await fetch("/api/cartaporte", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "validate", empresa_id: selectedCompanyId, cartaporte: draft, rfc }),
      });
      const data = await res.json();
      if (!data.ok) {
        setStatus((data.data?.errors || [data.error || "Carta Porte invalida"]).join("; "));
        return;
      }
      setValidated(true);
      setStatus("Validacion local correcta. Lista para intentar timbrado cuando existan CSD/PAC.");
    } catch {
      setStatus("Error de conexion");
    } finally {
      setValidating(false);
    }
  }

  async function handleStamp() {
    if (!draft || !stampFolio) return;
    setStamping(true);
    setStatus("");
    try {
      const res = await fetch("/api/cartaporte", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "stamp", empresa_id: selectedCompanyId, stamp_folio: stampFolio, cartaporte: draft, rfc, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al timbrar"); return; }
      const stamp = data.data?.cartaporte_stamp;
      setStatus(`Timbrado: ${stamp?.stamp_status} - uuid_sat: ${stamp?.uuid_sat || "-"}${data.data?.warnings?.length ? " (" + data.data.warnings.join("; ") + ")" : ""}`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setStamping(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Carta Porte</h1>
      <p className="text-muted text-sm mb-6">Complemento Carta Porte del CFDI: armar draft, validar y timbrar</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card">
              <h2 className="font-semibold mb-4">Armar draft</h2>
              <form onSubmit={handleBuild} className="space-y-3">
                <div>
                  <label className="label">Folio de viaje</label>
                  <input className="input font-mono" list="cp-trips" placeholder="T-0001" value={form.trip_folio} onChange={(e) => setForm((f) => ({ ...f, trip_folio: e.target.value.toUpperCase() }))} required />
                  <datalist id="cp-trips">{trips.map((trip: any) => <option key={trip.trip_folio} value={trip.trip_folio}>{trip.origin} - {trip.destination}</option>)}</datalist>
                </div>
                <div>
                  <label className="label">Tipo CFDI</label>
                  <select className="input" value={form.cfdi_type} onChange={(e) => setForm((f) => ({ ...f, cfdi_type: e.target.value }))}>
                    <option value="traslado">Traslado</option>
                    <option value="ingreso">Ingreso</option>
                  </select>
                </div>
                <div><label className="label">Descripcion mercancia</label><input className="input" value={form.descripcion} onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))} required /></div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Cantidad</label><input type="number" className="input" value={form.cantidad} onChange={(e) => setForm((f) => ({ ...f, cantidad: e.target.value }))} required /></div>
                  <div><label className="label">Peso kg</label><input type="number" className="input" value={form.peso_kg} onChange={(e) => setForm((f) => ({ ...f, peso_kg: e.target.value }))} required /></div>
                  <div><label className="label">Clave SAT</label><input className="input" placeholder="27111700" value={form.clave_prod_serv} onChange={(e) => setForm((f) => ({ ...f, clave_prod_serv: e.target.value }))} required /></div>
                </div>
                <button type="submit" className="btn-primary w-full" disabled={saving}>{saving ? "Armando..." : "Armar draft"}</button>
              </form>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Validar y timbrar</h2>
              <div className="space-y-3">
                <div><label className="label">Folio del draft</label><input className="input font-mono" placeholder="CP-0001" value={stampFolio} onChange={(e) => setStampFolio(e.target.value.toUpperCase())} disabled={!draft} /></div>
                <div><label className="label">RFC emisor</label><input className="input font-mono" placeholder="XAXX010101000" value={rfc} onChange={(e) => { setRfc(e.target.value.toUpperCase()); setValidated(false); }} disabled={!draft} /></div>
                <button type="button" className="btn-ghost w-full" onClick={handleValidate} disabled={!draft || validating}>{validating ? "Validando..." : validated ? "Validado" : "Validar local"}</button>
                <button type="button" className="btn-primary w-full" onClick={handleStamp} disabled={!draft || !validated || stamping || !rfc}>{stamping ? "Timbrando..." : "Timbrar"}</button>
                {!draft && <p className="text-muted text-xs">Primero arma un draft para poder timbrar.</p>}
                {draft && !validated && <p className="text-muted text-xs">El timbrado queda bloqueado hasta validar estructura, mercancias y RFC.</p>}
              </div>
              {draft && (
                <div className="mt-4 pt-4 border-t border-border text-sm space-y-1">
                  <p><span className="text-muted">Ruta:</span> {draft.origin} - {draft.destination}</p>
                  <p><span className="text-muted">Unidad:</span> {draft.unit_plate || "-"}</p>
                  <p><span className="text-muted">Operador:</span> {draft.driver_name || "-"} ({draft.driver_license || "-"})</p>
                </div>
              )}
            </div>
          </div>

          <div className="card mt-4">
            <h2 className="font-semibold mb-4">Historial de timbrado</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-muted"><tr><th className="text-left py-2">Folio</th><th className="text-left py-2">Viaje</th><th className="text-left py-2">Tipo</th><th className="text-left py-2">Status</th><th className="text-left py-2">UUID SAT</th></tr></thead>
                <tbody>
                  {stamps.map((stamp: any) => (
                    <tr key={stamp.stamp_folio} className="border-t border-border">
                      <td className="py-2 font-mono">{stamp.stamp_folio}</td>
                      <td className="py-2 font-mono">{stamp.trip_folio || "-"}</td>
                      <td className="py-2">{stamp.cfdi_type || "-"}</td>
                      <td className="py-2">{stamp.stamp_status || "-"}</td>
                      <td className="py-2 font-mono">{stamp.uuid_sat || "-"}</td>
                    </tr>
                  ))}
                  {!stamps.length && <tr><td className="py-4 text-muted" colSpan={5}>{ops.loading ? "Cargando..." : "Sin timbres registrados."}</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
