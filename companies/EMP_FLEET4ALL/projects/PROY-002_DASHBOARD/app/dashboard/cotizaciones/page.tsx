"use client";
import { useState } from "react";
import { useCompany } from "@/lib/useCompany";
import { useFleetOps } from "@/lib/useFleetOps";

const fmt = (n: number, c = "MXN") => Number(n || 0).toLocaleString("es-MX", { style: "currency", currency: c });

export default function CotizacionesPage() {
  const { selectedCompanyId, loading: loadingCompany } = useCompany();
  const ops = useFleetOps(selectedCompanyId, ["rates", "quotes", "drivers", "units"]);
  const [rateForm, setRateForm] = useState({ origin: "", destination: "", cargo_type: "", base_price: "", price_per_km: "", price_per_ton: "" });
  const [savingRate, setSavingRate] = useState(false);

  const [quoteForm, setQuoteForm] = useState({ customer: "", origin: "", destination: "", cargo_type: "", weight_tons: "", distance_km: "", departure_date: "", driver_key: "", unit_key: "" });
  const [quote, setQuote] = useState<any>(null);
  const [quoting, setQuoting] = useState(false);
  const [accepting, setAccepting] = useState(false);

  const [status, setStatus] = useState("");
  const rates = ops.data?.rates || [];
  const quotes = ops.data?.quotes || [];
  const drivers = ops.data?.drivers || [];
  const units = ops.data?.units || [];

  async function handleRate(e: React.FormEvent) {
    e.preventDefault();
    setSavingRate(true);
    setStatus("");
    try {
      const res = await fetch("/api/cotizaciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "rate", empresa_id: selectedCompanyId, ...rateForm, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) { setStatus(data.error || "Error al crear tarifa"); return; }
      setStatus(`Tarifa ${data.data?.rate?.rate_key} creada.`);
      setRateForm({ origin: "", destination: "", cargo_type: "", base_price: "", price_per_km: "", price_per_ton: "" });
    } catch {
      setStatus("Error de conexion");
    } finally {
      setSavingRate(false);
    }
  }

  async function buildQuote(accept: boolean) {
    if (accept) setAccepting(true); else setQuoting(true);
    setStatus("");
    try {
      const res = await fetch("/api/cotizaciones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "quote", empresa_id: selectedCompanyId, ...quoteForm, accept, dry_run: false }),
      });
      const data = await res.json();
      if (!data.ok) {
        const suggestions = data.data?.warnings;
        setStatus(data.error === "no_rate_found" && suggestions?.length
          ? `Sin tarifa exacta. Tarifas cercanas: ${suggestions.map((s: any) => s.rate_key).join(", ")}`
          : (data.error || "Error al cotizar"));
        return;
      }
      setQuote(data.data?.quote || null);
      setStatus(accept ? `Cotizacion aceptada, viaje ${data.data?.quote?.trip_folio || "-"} creado.` : `Cotizacion ${data.data?.quote?.quote_folio} generada.`);
    } catch {
      setStatus("Error de conexion");
    } finally {
      setQuoting(false);
      setAccepting(false);
    }
  }

  if (loadingCompany) return null;

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Cotizaciones</h1>
      <p className="text-muted text-sm mb-6">Tarifario y cotizador de fletes</p>

      {!selectedCompanyId ? (
        <div className="card text-center py-12"><p className="text-muted">Selecciona una empresa en el header.</p></div>
      ) : (
        <>
          <datalist id="quote-drivers">{drivers.map((driver: any) => <option key={driver.driver_key} value={driver.driver_key}>{driver.full_name}</option>)}</datalist>
          <datalist id="quote-units">{units.map((unit: any) => <option key={unit.unit_key} value={unit.unit_key}>{unit.plate || unit.unit_key}</option>)}</datalist>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card">
              <h2 className="font-semibold mb-4">Nueva tarifa</h2>
              <form onSubmit={handleRate} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Origen</label><input className="input" value={rateForm.origin} onChange={(e) => setRateForm((f) => ({ ...f, origin: e.target.value }))} required /></div>
                  <div><label className="label">Destino</label><input className="input" value={rateForm.destination} onChange={(e) => setRateForm((f) => ({ ...f, destination: e.target.value }))} required /></div>
                </div>
                <div><label className="label">Tipo de carga</label><input className="input" value={rateForm.cargo_type} onChange={(e) => setRateForm((f) => ({ ...f, cargo_type: e.target.value }))} /></div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Base</label><input type="number" className="input" value={rateForm.base_price} onChange={(e) => setRateForm((f) => ({ ...f, base_price: e.target.value }))} required /></div>
                  <div><label className="label">Por km</label><input type="number" className="input" value={rateForm.price_per_km} onChange={(e) => setRateForm((f) => ({ ...f, price_per_km: e.target.value }))} /></div>
                  <div><label className="label">Por ton</label><input type="number" className="input" value={rateForm.price_per_ton} onChange={(e) => setRateForm((f) => ({ ...f, price_per_ton: e.target.value }))} /></div>
                </div>
                <button type="submit" className="btn-primary w-full" disabled={savingRate}>{savingRate ? "Guardando..." : "Crear tarifa"}</button>
              </form>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Cotizar</h2>
              <div className="space-y-3">
                <div><label className="label">Cliente</label><input className="input" value={quoteForm.customer} onChange={(e) => setQuoteForm((f) => ({ ...f, customer: e.target.value }))} required /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="label">Origen</label><input className="input" value={quoteForm.origin} onChange={(e) => setQuoteForm((f) => ({ ...f, origin: e.target.value }))} required /></div>
                  <div><label className="label">Destino</label><input className="input" value={quoteForm.destination} onChange={(e) => setQuoteForm((f) => ({ ...f, destination: e.target.value }))} required /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Carga</label><input className="input" value={quoteForm.cargo_type} onChange={(e) => setQuoteForm((f) => ({ ...f, cargo_type: e.target.value }))} /></div>
                  <div><label className="label">Ton</label><input type="number" className="input" value={quoteForm.weight_tons} onChange={(e) => setQuoteForm((f) => ({ ...f, weight_tons: e.target.value }))} /></div>
                  <div><label className="label">Distancia km</label><input type="number" className="input" value={quoteForm.distance_km} onChange={(e) => setQuoteForm((f) => ({ ...f, distance_km: e.target.value }))} /></div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="label">Salida</label><input type="date" className="input" value={quoteForm.departure_date} onChange={(e) => setQuoteForm((f) => ({ ...f, departure_date: e.target.value }))} /></div>
                  <div><label className="label">Operador</label><input className="input" list="quote-drivers" value={quoteForm.driver_key} onChange={(e) => setQuoteForm((f) => ({ ...f, driver_key: e.target.value }))} /></div>
                  <div><label className="label">Unidad</label><input className="input" list="quote-units" value={quoteForm.unit_key} onChange={(e) => setQuoteForm((f) => ({ ...f, unit_key: e.target.value }))} /></div>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn-ghost flex-1" onClick={() => buildQuote(false)} disabled={quoting}>{quoting ? "Cotizando..." : "Cotizar"}</button>
                  <button type="button" className="btn-primary flex-1" onClick={() => buildQuote(true)} disabled={accepting}>{accepting ? "Creando viaje..." : "Cotizar y aceptar"}</button>
                </div>
              </div>
              {quote && (
                <div className="mt-4 pt-4 border-t border-border text-sm space-y-1">
                  <p><span className="text-muted">Folio:</span> <span className="font-mono">{quote.quote_folio}</span></p>
                  <p><span className="text-muted">Precio:</span> <span className="font-semibold">{fmt(quote.quoted_price, quote.currency)}</span></p>
                  <p><span className="text-muted">Viaje:</span> <span className="font-mono">{quote.trip_folio || "-"}</span></p>
                  <p><span className="text-muted">Vigencia:</span> {quote.valid_until}</p>
                  <p><span className="text-muted">Status:</span> {quote.status}</p>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2 mt-4">
            <div className="card">
              <h2 className="font-semibold mb-4">Tarifas activas</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-muted"><tr><th className="text-left py-2">Clave</th><th className="text-left py-2">Ruta</th><th className="text-left py-2">Carga</th><th className="text-left py-2">Base</th></tr></thead>
                  <tbody>
                    {rates.map((rate: any) => (
                      <tr key={rate.rate_key} className="border-t border-border">
                        <td className="py-2 font-mono">{rate.rate_key}</td>
                        <td className="py-2">{rate.origin} - {rate.destination}</td>
                        <td className="py-2">{rate.cargo_type || "general"}</td>
                        <td className="py-2">{fmt(rate.base_price, rate.currency)}</td>
                      </tr>
                    ))}
                    {!rates.length && <tr><td className="py-4 text-muted" colSpan={4}>{ops.loading ? "Cargando..." : "Sin tarifas."}</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <h2 className="font-semibold mb-4">Cotizaciones recientes</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-muted"><tr><th className="text-left py-2">Folio</th><th className="text-left py-2">Cliente</th><th className="text-left py-2">Precio</th><th className="text-left py-2">Status</th></tr></thead>
                  <tbody>
                    {quotes.map((row: any) => (
                      <tr key={row.quote_folio} className="border-t border-border">
                        <td className="py-2 font-mono">{row.quote_folio}</td>
                        <td className="py-2">{row.customer}</td>
                        <td className="py-2">{fmt(row.quoted_price, row.currency)}</td>
                        <td className="py-2">{row.status}</td>
                      </tr>
                    ))}
                    {!quotes.length && <tr><td className="py-4 text-muted" colSpan={4}>{ops.loading ? "Cargando..." : "Sin cotizaciones."}</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}

      {status && <p className="mt-4 text-sm bg-card border border-border rounded-lg px-3 py-2">{status}</p>}
    </div>
  );
}
