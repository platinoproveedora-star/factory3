"use client";

import { useEffect, useState } from "react";

type IssuerProfile = { id: string; rfc: string; legal_name: string; status: string };
type Party = { id: string; rfc: string; legal_name: string; party_type: string; cfdi_use_default?: string };
type FolioSeries = { id: string; series: string; cfdi_type: string; is_default: boolean };
type Product = { id: string; source_product_key: string; fiscal_product_name: string; sat_product_key: string; sat_unit_key: string; status: string };
type Item = { source_product_key: string; description: string; quantity: number; unit_price: number; iva_rate: number };

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

const PAYMENT_FORMS = [
  { code: "01", label: "01 - Efectivo" },
  { code: "03", label: "03 - Transferencia" },
  { code: "04", label: "04 - Tarjeta de crédito" },
  { code: "28", label: "28 - Tarjeta de débito" },
  { code: "99", label: "99 - Por definir" },
];

// Catalogo oficial c_UsoCFDI (SAT) — solo las claves relevantes para
// facturas B2B que emite la empresa (se omiten D01-D10, deducciones
// personales de individuos).
const USO_CFDI_CATALOG = [
  { code: "G01", label: "G01 - Adquisición de mercancías" },
  { code: "G02", label: "G02 - Devoluciones, descuentos o bonificaciones" },
  { code: "G03", label: "G03 - Gastos en general" },
  { code: "I01", label: "I01 - Construcciones" },
  { code: "I02", label: "I02 - Mobiliario y equipo de oficina por inversiones" },
  { code: "I03", label: "I03 - Equipo de transporte" },
  { code: "I04", label: "I04 - Equipo de cómputo y accesorios" },
  { code: "I05", label: "I05 - Dados, troqueles, moldes, matrices y otros activos" },
  { code: "I06", label: "I06 - Comunicaciones telefónicas" },
  { code: "I07", label: "I07 - Comunicaciones satelitales" },
  { code: "I08", label: "I08 - Otra maquinaria y equipo" },
  { code: "S01", label: "S01 - Sin efectos fiscales" },
];

const emptyItem = (): Item => ({ source_product_key: "", description: "", quantity: 1, unit_price: 0, iva_rate: 0.16 });

export default function NewInvoiceForm() {
  const [issuers, setIssuers] = useState<IssuerProfile[]>([]);
  const [parties, setParties] = useState<Party[]>([]);
  const [series, setSeries] = useState<FolioSeries[]>([]);
  const [products, setProducts] = useState<Product[]>([]);

  const [issuerRfc, setIssuerRfc] = useState("");
  const [seriesCode, setSeriesCode] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"PUE" | "PPD">("PUE");
  const [paymentForm, setPaymentForm] = useState("01");

  const [existingPartyRfc, setExistingPartyRfc] = useState("");
  const [newParty, setNewParty] = useState(false);
  const [newPartyRfc, setNewPartyRfc] = useState("");
  const [newPartyName, setNewPartyName] = useState("");
  const [newPartyRegime, setNewPartyRegime] = useState("");
  const [newPartyZip, setNewPartyZip] = useState("");
  const [newPartyCfdiUse, setNewPartyCfdiUse] = useState("G03");
  const [usoCfdi, setUsoCfdi] = useState("");
  const [usoCfdiTouched, setUsoCfdiTouched] = useState(false);

  const [items, setItems] = useState<Item[]>([emptyItem()]);
  const [preview, setPreview] = useState<any>(null);
  const [built, setBuilt] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const [issuerRes, partyRes, seriesRes, productRes] = await Promise.all([
        api<{ issuer_profiles: IssuerProfile[] }>("/api/factu4all/issuer"),
        api<{ parties: Party[] }>("/api/factu4all/parties?party_type=customer"),
        api<{ folio_series: FolioSeries[] }>("/api/factu4all/series"),
        api<{ products: Product[] }>("/api/factu4all/products"),
      ]);
      const issuerList = issuerRes.data?.issuer_profiles || [];
      setIssuers(issuerList);
      if (issuerList[0]) setIssuerRfc(issuerList[0].rfc);
      setParties(partyRes.data?.parties || []);
      const seriesList = seriesRes.data?.folio_series || [];
      setSeries(seriesList);
      const def = seriesList.find((row) => row.is_default);
      if (def) setSeriesCode(def.series);
      setProducts((productRes.data?.products || []).filter((p) => p.status === "ready"));
    })();
  }, []);

  useEffect(() => {
    if (usoCfdiTouched) return;
    if (newParty) {
      setUsoCfdi(newPartyCfdiUse);
      return;
    }
    const party = parties.find((p) => p.rfc === existingPartyRfc);
    if (party?.cfdi_use_default) setUsoCfdi(party.cfdi_use_default);
  }, [existingPartyRfc, newParty, newPartyCfdiUse, parties, usoCfdiTouched]);

  function updateItem(index: number, patch: Partial<Item>) {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  function selectProduct(index: number, sourceProductKey: string) {
    const product = products.find((p) => p.source_product_key === sourceProductKey);
    updateItem(index, {
      source_product_key: sourceProductKey,
      description: product ? product.fiscal_product_name : "",
    });
  }

  function addItem() {
    setItems((prev) => [...prev, emptyItem()]);
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function ensureParty(): Promise<string> {
    if (!newParty) return existingPartyRfc;
    const res = await api("/api/factu4all/parties", {
      method: "POST",
      body: JSON.stringify({
        rfc: newPartyRfc,
        party_type: "customer",
        legal_name: newPartyName,
        tax_regime: newPartyRegime,
        tax_zip_code: newPartyZip,
        cfdi_use_default: newPartyCfdiUse,
      }),
    });
    if (!res.ok) throw new Error(res.error || "No se pudo crear el cliente fiscal");
    return newPartyRfc;
  }

  function buildPayload(partyRfc: string) {
    return {
      issuer_rfc: issuerRfc,
      party_rfc: partyRfc,
      party_type: "customer",
      cfdi_type: "ingreso",
      series: seriesCode,
      payment_method: paymentMethod,
      payment_form: paymentForm,
      uso_cfdi: usoCfdi,
      items: items.map((item) => ({
        source_product_key: item.source_product_key || undefined,
        description: item.description,
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price),
        iva_rate: Number(item.iva_rate),
      })),
    };
  }

  async function handlePreview() {
    setBusy(true);
    setMessage("");
    try {
      const partyRfc = newParty ? newPartyRfc : existingPartyRfc;
      if (!partyRfc) throw new Error("Selecciona o crea un cliente fiscal");
      const res = await api("/api/factu4all/invoices", { method: "POST", body: JSON.stringify({ ...buildPayload(partyRfc), preview: true }) });
      if (!res.ok) throw new Error(res.error);
      setPreview((res.data as any)?.cfdi_document);
      setBuilt(null);
    } catch (error: any) {
      setMessage(error?.message || "Error al calcular la vista previa");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate() {
    setBusy(true);
    setMessage("");
    try {
      const partyRfc = await ensureParty();
      if (!partyRfc) throw new Error("Selecciona o crea un cliente fiscal");
      const res = await api("/api/factu4all/invoices", { method: "POST", body: JSON.stringify(buildPayload(partyRfc)) });
      if (!res.ok) throw new Error(res.error);
      setBuilt((res.data as any)?.cfdi_document);
      setMessage("Factura creada como borrador.");
    } catch (error: any) {
      setMessage(error?.message || "Error al crear la factura");
    } finally {
      setBusy(false);
    }
  }

  async function handleStamp() {
    if (!built?.folio) return;
    setBusy(true);
    setMessage("Timbrando...");
    try {
      const res = await api("/api/factu4all/invoices/stamp", { method: "POST", body: JSON.stringify({ folio: built.folio }) });
      if (!res.ok) throw new Error(res.error);
      setBuilt((res.data as any)?.cfdi_document);
      setMessage("Factura timbrada.");
    } catch (error: any) {
      setMessage(error?.message || "Error al timbrar");
    } finally {
      setBusy(false);
    }
  }

  const totals = preview || built;

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <section className="card grid gap-3 sm:grid-cols-3">
        <label className="block">
          <span className="label">Emisor (RFC)</span>
          <select className="input" value={issuerRfc} onChange={(e) => setIssuerRfc(e.target.value)}>
            {issuers.map((row) => (
              <option key={row.id} value={row.rfc}>
                {row.rfc} — {row.legal_name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="label">Serie</span>
          <select className="input" value={seriesCode} onChange={(e) => setSeriesCode(e.target.value)}>
            {series.filter((row) => row.cfdi_type === "ingreso").map((row) => (
              <option key={row.id} value={row.series}>
                {row.series}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="label">Método de pago</span>
          <select className="input" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as "PUE" | "PPD")}>
            <option value="PUE">PUE - Pago en una exhibición</option>
            <option value="PPD">PPD - Pago en parcialidades</option>
          </select>
        </label>
        <label className="block sm:col-span-3">
          <span className="label">Forma de pago</span>
          <select className="input" value={paymentForm} onChange={(e) => setPaymentForm(e.target.value)}>
            {PAYMENT_FORMS.map((row) => (
              <option key={row.code} value={row.code}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Cliente fiscal</h2>
        <div className="mt-2 flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="radio" checked={!newParty} onChange={() => setNewParty(false)} /> Cliente existente
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={newParty} onChange={() => setNewParty(true)} /> Crear cliente nuevo
          </label>
        </div>

        {!newParty ? (
          <select className="input mt-3" value={existingPartyRfc} onChange={(e) => setExistingPartyRfc(e.target.value)}>
            <option value="">Selecciona un cliente</option>
            {parties.map((row) => (
              <option key={row.id} value={row.rfc}>
                {row.rfc} — {row.legal_name}
              </option>
            ))}
          </select>
        ) : (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="label">RFC</span>
              <input className="input" value={newPartyRfc} onChange={(e) => setNewPartyRfc(e.target.value.toUpperCase())} />
            </label>
            <label className="block">
              <span className="label">Razón social</span>
              <input className="input" value={newPartyName} onChange={(e) => setNewPartyName(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Régimen fiscal (clave SAT)</span>
              <input className="input" placeholder="ej. 616" value={newPartyRegime} onChange={(e) => setNewPartyRegime(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Código postal</span>
              <input className="input" value={newPartyZip} onChange={(e) => setNewPartyZip(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Uso CFDI por default (queda guardado en el cliente)</span>
              <input className="input" value={newPartyCfdiUse} onChange={(e) => setNewPartyCfdiUse(e.target.value.toUpperCase())} />
            </label>
          </div>
        )}

        <label className="mt-3 block">
          <span className="label">Uso CFDI de esta factura</span>
          <select
            className="input"
            value={usoCfdi}
            onChange={(e) => {
              setUsoCfdi(e.target.value);
              setUsoCfdiTouched(true);
            }}
          >
            <option value="">Selecciona un uso CFDI</option>
            {USO_CFDI_CATALOG.map((row) => (
              <option key={row.code} value={row.code}>
                {row.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">Obligatorio para timbrar — precargado con el default del cliente, editable por factura.</p>
        </label>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Conceptos</h2>
        <div className="mt-3 space-y-3">
          {items.map((item, index) => {
            const product = products.find((p) => p.source_product_key === item.source_product_key);
            return (
              <div key={index} className="grid gap-2 sm:grid-cols-[1.4fr_1.6fr_0.8fr_1fr_1fr_auto]">
                <select className="input" value={item.source_product_key} onChange={(e) => selectProduct(index, e.target.value)}>
                  <option value="">Concepto manual</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.source_product_key}>
                      {p.fiscal_product_name} ({p.sat_product_key})
                    </option>
                  ))}
                </select>
                <input
                  className="input"
                  placeholder="Descripción"
                  value={item.description}
                  disabled={Boolean(item.source_product_key)}
                  onChange={(e) => updateItem(index, { description: e.target.value })}
                />
                <input className="input" type="number" step="0.01" placeholder="Cantidad" value={item.quantity} onChange={(e) => updateItem(index, { quantity: Number(e.target.value) })} />
                <input className="input" type="number" step="0.01" placeholder="Precio unitario" value={item.unit_price} onChange={(e) => updateItem(index, { unit_price: Number(e.target.value) })} />
                <input className="input" type="number" step="0.01" placeholder="IVA" value={item.iva_rate} onChange={(e) => updateItem(index, { iva_rate: Number(e.target.value) })} />
                <button type="button" className="btn-ghost px-3" onClick={() => removeItem(index)}>
                  Quitar
                </button>
                {product && (
                  <p className="col-span-full text-xs text-slate-400">
                    Clave SAT {product.sat_product_key} · Unidad {product.sat_unit_key}
                  </p>
                )}
              </div>
            );
          })}
        </div>
        <button type="button" className="btn-ghost mt-3 px-3 py-2" onClick={addItem}>
          + Agregar concepto
        </button>
        <p className="mt-2 text-xs text-slate-400">
          Los conceptos manuales (sin producto) no traen clave SAT — hay que completarlos en Productos fiscales antes de poder timbrar.
        </p>
      </section>

      {totals && (
        <section className="card">
          <h2 className="text-sm font-semibold uppercase text-slate-500">Totales</h2>
          <p className="mt-2 text-sm">Subtotal: ${totals.subtotal}</p>
          <p className="text-sm">IVA: ${totals.tax_total}</p>
          <p className="text-sm font-semibold">Total: ${totals.total}</p>
          {built?.folio && <p className="mt-2 text-sm text-slate-500">Folio: {built.folio} — estado: {built.status}</p>}
          {built?.uuid && <p className="text-sm text-slate-500">UUID: {built.uuid}</p>}
        </section>
      )}

      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost px-4 py-2" disabled={busy} onClick={handlePreview}>
          Vista previa
        </button>
        <button className="btn-primary px-4 py-2" disabled={busy || Boolean(built)} onClick={handleCreate}>
          Crear factura (borrador)
        </button>
        {built?.folio && built.status !== "stamped" && built.status !== "simulated" && (
          <button className="btn-primary px-4 py-2" disabled={busy} onClick={handleStamp}>
            Timbrar
          </button>
        )}
      </div>
    </div>
  );
}
