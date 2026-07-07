"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function LiquidacionesPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const ops = useFleetOps(selectedCompanyId, ["drivers", "settlements"]);
  const [advForm, setAdvForm] = useState({ driver_key: "", amount: "", advance_date: "", concept: "" });
  const [savingAdv, setSavingAdv] = useState(false);

  const [calcForm, setCalcForm] = useState({ driver_key: "", from: "", to: "" });
  const [settlement, setSettlement] = useState<any>(null);
  const [calculating, setCalculating] = useState(false);
  const [approving, setApproving] = useState(false);

  const [status, setStatus] = useState("");
  const drivers = ops.data?.drivers || [];
  const settlements = ops.data?.settlements || [];

  async function handleAdvance(e: React.FormEvent) {
    e.preventDefault();
    setSavingAdv(true);
    setStatus("");
    try {
      const res = await fetch("/api/liquidaciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "advance", empresa_id: selectedCompanyId, ...advForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al registrar anticipo"); return; }
      setStatus(`Anticipo ${data.data?.advance?.advance_folio} registrado.`);
      setAdvForm({ driver_key: "", amount: "", advance_date: "", concept: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingAdv(false);
    }
  }

  async function calculate(approve: boolean) {
    if (approve) setApproving(true); else setCalculating(true);
    setStatus("");
    try {
      const res = await fetch("/api/liquidaciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "calculate",
          empresa_id: selectedCompanyId,
          driver_key: calcForm.driver_key,
          period: { from: calcForm.from, to: calcForm.to },
          approve,
          dry_run: !approve,
        }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al calcular liquidacion"); return; }
      setSettlement(data.data?.settlement || null);
      setStatus(approve ? "Liquidacion aprobada." : "Previsualizacion calculada. No se persistio.");
    } catch {
      setStatus("Error de conexion");
    } finally {
      setCalculating(false);
      setApproving(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Liquidaciones</h1>
      <p className="text-muted text-sm mb-6">Anticipos y liquidaciones de operadores por periodo</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <>
          <datalist id="drivers-list">{drivers.map((driver: any) => <option key={driver.driver_key} value={driver.driver_key}>{driver.full_name}</option>)}</datalist>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card">
              <h2 className="font-semibold mb-4">Registrar anticipo</h2>
              <form onSubmit={handleAdvance} className="space-y-3">
                <div><label className="label">Operador</label><input className="input" list="drivers-list" value={advForm.driver_key} onChange={(e) => setAdvForm((f) => ({ ...f, driver_key: e.target.value }))} required /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Monto</label><input type="number" className="input" value={advForm.amount} onChange={(e) => setAdvForm((f) => ({ ...f, amount: e.target.value }))} required /></div>
                  <div><label className="label">Fecha</label><input type="date" className="input" value={advForm.advance_date} onChange={(e) => setAdvForm((f) => ({ ...f, advance_date: e.target.value }))} /></div>
                </div>
                <div><label className="label">Concepto</label><input className="input" value={advForm.concept} onChange={(e) => setAdvForm((f) => ({ ...f, concept: e.target.value }))} /></div>
                <button type="submit" className="btn-primary w-full" disabled={savingAdv}>{savingAdv ? "Guardando..." : "Registrar anticipo"}</button>
              </form>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Calcular liquidacion</h2>
              <div className="space-y-3">
                <div><label className="label">Operador</label><input className="input" list="drivers-list" value={calcForm.driver_key} onChange={(e) => { setCalcForm((f) => ({ ...f, driver_key: e.target.value })); setSettlement(null); }} required /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Desde</label><input type="date" className="input" value={calcForm.from} onChange={(e) => setCalcForm((f) => ({ ...f, from: e.target.value }))} /></div>
                  <div><label className="label">Hasta</label><input type="date" className="input" value={calcForm.to} onChange={(e) => setCalcForm((f) => ({ ...f, to: e.target.value }))} /></div>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn-ghost flex-1" onClick={() => calculate(false)} disabled={calculating || !calcForm.driver_key}>{calculating ? "Calculando..." : "Previsualizar"}</button>
                  <button type="button" className="btn-primary flex-1" onClick={() => calculate(true)} disabled={approving || !calcForm.driver_key || !settlement}>{approving ? "Aprobando..." : "Aprobar"}</button>
                </div>
              </div>
              {settlement && (
                <div className="mt-4 pt-4 border-t border-border text-sm space-y-1">
                  <p><span className="text-muted">Folio:</span> <span className="font-mono">{settlement.settlement_folio}</span></p>
                  <p><span className="text-muted">Viajes:</span> {settlement.trips_included?.length || 0}</p>
                  <p><span className="text-muted">Bruto:</span> {fmt(settlement.gross_amount, settlement.currency)}</p>
                  <p><span className="text-muted">Anticipos:</span> {fmt(settlement.advances_deducted, settlement.currency)}</p>
                  <p><span className="text-muted">Neto:</span> <span className="font-semibold text-green-400">{fmt(settlement.net_amount, settlement.currency)}</span></p>
                  <p><span className="text-muted">Status:</span> {settlement.status}</p>
                </div>
              )}
            </div>
          </div>

          <div className="card mt-4">
            <h2 className="font-semibold mb-4">Historial</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-muted"><tr><th className="text-left py-2">Folio</th><th className="text-left py-2">Operador</th><th className="text-left py-2">Periodo</th><th className="text-left py-2">Neto</th><th className="text-left py-2">Status</th></tr></thead>
                <tbody>
                  {settlements.map((row: any) => (
                    <tr key={row.settlement_folio} className="border-t border-border">
                      <td className="py-2 font-mono">{row.settlement_folio}</td>
                      <td className="py-2">{row.driver_key}</td>
                      <td className="py-2">{row.period_from || "-"} / {row.period_to || "-"}</td>
                      <td className="py-2">{fmt(row.net_amount, row.currency)}</td>
                      <td className="py-2">{row.status}</td>
                    </tr>
                  ))}
                  {!settlements.length && <tr><td className="py-4 text-muted" colSpan={5}>{ops.loading ? "Cargando..." : "Sin liquidaciones."}</td></tr>}
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
