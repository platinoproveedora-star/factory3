"use client";

import { useEffect, useState } from "react";

type PreviewItem = { descripcion: string; cantidad: string; clave_prod_serv: string; clave_unidad: string };
type Preview = { uuid: string; rfc_emisor: string; nombre_emisor: string; total: string; items: PreviewItem[] };
type ImportedItem = { descripcion: string; cantidad: number; product_id: string; product_created: boolean; sat_product_key: string };
type BatchResult = {
  total: number;
  imported: number;
  skipped_duplicates: number;
  failed: number;
  failed_items: { index: number; error: string; detail?: string }[];
};
type PurchaseInvoice = {
  id: string;
  folio: string;
  cfdi_folio: string;
  party_rfc_snapshot: string;
  party_legal_name_snapshot: string;
  total: number;
  uuid: string;
  created_at: string;
};
type PendingOrder = {
  id: string;
  folio: string;
  source_id: string;
  party_rfc_snapshot: string;
  party_legal_name_snapshot: string;
  total: number;
  created_at: string;
  metadata?: { expected_date?: string; items?: { source_product_key?: string; description?: string; quantity?: number; estimated_unit_price?: number }[] };
};
type PoItemRow = { source_product_key: string; quantity: number; estimated_unit_price: number };

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

export default function PurchasesForm() {
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [xml, setXml] = useState("");
  const [xmls, setXmls] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [imported, setImported] = useState<{ items: ImportedItem[] } | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [invoices, setInvoices] = useState<PurchaseInvoice[]>([]);
  const [pendingOrders, setPendingOrders] = useState<PendingOrder[]>([]);
  const [poReference, setPoReference] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const [poForm, setPoForm] = useState({ source_id: "", supplier_rfc: "", supplier_name: "", expected_date: "" });
  const [poItems, setPoItems] = useState<PoItemRow[]>([{ source_product_key: "", quantity: 1, estimated_unit_price: 0 }]);

  async function refresh() {
    const [invRes, poRes] = await Promise.all([
      api<{ cfdi_documents: PurchaseInvoice[] }>("/api/factu4all/purchases"),
      api<{ purchase_orders: PendingOrder[] }>("/api/factu4all/purchase-orders"),
    ]);
    setInvoices(invRes.data?.cfdi_documents || []);
    setPendingOrders(poRes.data?.purchase_orders || []);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setPreview(null);
    setImported(null);
    setBatchResult(null);
    setMessage("");
    try {
      const list = Array.from(files);
      const texts = await Promise.all(list.map((f) => readFileAsText(f)));
      const nonEmpty = texts.filter((t) => t.trim());
      if (!nonEmpty.length) {
        setMessage("Los archivos se leyeron vacíos.");
        return;
      }
      setFileNames(list.map((f) => f.name));
      if (list.length === 1) {
        setXml(nonEmpty[0]);
        setXmls([]);
      } else {
        setXmls(nonEmpty);
        setXml("");
      }
    } catch (error: any) {
      setMessage(`No se pudo leer alguno de los archivos: ${error?.message || error}`);
    }
  }

  async function handlePreview() {
    if (!xml) return;
    setBusy(true);
    setMessage("");
    const res = await api("/api/factu4all/purchases", { method: "POST", body: JSON.stringify({ xml, preview: true }) });
    setBusy(false);
    if (!res.ok) {
      setMessage(res.error || "Error al leer el XML");
      return;
    }
    setPreview(res.data as Preview);
  }

  async function handleImport() {
    if (!xml) return;
    setBusy(true);
    setMessage("");
    const res = await api("/api/factu4all/purchases", { method: "POST", body: JSON.stringify({ xml, preview: false, po_reference: poReference || undefined }) });
    setBusy(false);
    if (!res.ok) {
      setMessage(res.error || "Error al importar");
      return;
    }
    setImported(res.data as { items: ImportedItem[] });
    setMessage(poReference ? "Factura importada — orden pendiente conciliada." : "Factura importada y kardex actualizado.");
    setXml("");
    setFileNames([]);
    setPreview(null);
    setPoReference("");
    refresh();
  }

  async function handleBatchImport() {
    if (!xmls.length) return;
    setBusy(true);
    setMessage("");
    const res = await api("/api/factu4all/purchases", { method: "POST", body: JSON.stringify({ xmls }) });
    setBusy(false);
    if (!res.ok) {
      setMessage(res.error || "Error al importar el lote");
      return;
    }
    setBatchResult(res.data as BatchResult);
    setXmls([]);
    setFileNames([]);
    refresh();
  }

  function updatePoItem(index: number, patch: Partial<PoItemRow>) {
    setPoItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  async function submitPurchaseOrder(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const res = await api("/api/factu4all/purchase-orders", {
      method: "POST",
      body: JSON.stringify({
        source_id: poForm.source_id,
        supplier_rfc: poForm.supplier_rfc.toUpperCase(),
        supplier_name: poForm.supplier_name,
        expected_date: poForm.expected_date || undefined,
        items: poItems.filter((item) => item.source_product_key),
      }),
    });
    setBusy(false);
    if (!res.ok) {
      setMessage(res.error || "Error al crear la orden de compra");
      return;
    }
    setMessage("Orden de compra registrada — pendiente de factura.");
    setPoForm({ source_id: "", supplier_rfc: "", supplier_name: "", expected_date: "" });
    setPoItems([{ source_product_key: "", quantity: 1, estimated_unit_price: 0 }]);
    refresh();
  }

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Órdenes de compra / remisiones pendientes</h2>
        <p className="mt-1 text-xs text-slate-500">
          Documento previo a la factura de egreso — no mueve inventario, solo queda como "falta esta factura". Lo normal es que el
          ERP la mande automático; este formulario es para capturarla a mano si hace falta.
        </p>

        <form onSubmit={submitPurchaseOrder} className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">Referencia (folio propio)</span>
            <input className="input" required value={poForm.source_id} onChange={(e) => setPoForm({ ...poForm, source_id: e.target.value })} placeholder="OC-0099" />
          </label>
          <label className="block">
            <span className="label">RFC proveedor</span>
            <input className="input" required value={poForm.supplier_rfc} onChange={(e) => setPoForm({ ...poForm, supplier_rfc: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Nombre proveedor</span>
            <input className="input" value={poForm.supplier_name} onChange={(e) => setPoForm({ ...poForm, supplier_name: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Fecha esperada</span>
            <input className="input" type="date" value={poForm.expected_date} onChange={(e) => setPoForm({ ...poForm, expected_date: e.target.value })} />
          </label>

          <div className="sm:col-span-2 space-y-2">
            <span className="label">Conceptos esperados</span>
            {poItems.map((item, index) => (
              <div key={index} className="grid gap-2 sm:grid-cols-3">
                <input className="input" placeholder="Clave / SKU" value={item.source_product_key} onChange={(e) => updatePoItem(index, { source_product_key: e.target.value })} />
                <input className="input" type="number" placeholder="Cantidad" value={item.quantity} onChange={(e) => updatePoItem(index, { quantity: Number(e.target.value) })} />
                <input className="input" type="number" placeholder="Precio estimado" value={item.estimated_unit_price} onChange={(e) => updatePoItem(index, { estimated_unit_price: Number(e.target.value) })} />
              </div>
            ))}
            <button type="button" className="btn-ghost px-3 py-1 text-xs" onClick={() => setPoItems((prev) => [...prev, { source_product_key: "", quantity: 1, estimated_unit_price: 0 }])}>
              + Agregar concepto
            </button>
          </div>

          <div className="sm:col-span-2">
            <button className="btn-primary px-4 py-2" type="submit" disabled={busy}>
              Registrar orden pendiente
            </button>
          </div>
        </form>

        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase text-slate-400">Pendientes ({pendingOrders.length})</h3>
          {pendingOrders.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">Todavía no hay órdenes de compra pendientes.</p>
          ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Referencia</th><th>Proveedor</th><th>Total estimado</th><th>Fecha esperada</th>
                </tr>
              </thead>
              <tbody>
                {pendingOrders.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.source_id}</td>
                    <td>
                      {row.party_legal_name_snapshot}
                      <div className="text-xs text-slate-400">{row.party_rfc_snapshot}</div>
                    </td>
                    <td>${row.total}</td>
                    <td className="text-xs text-slate-500">{row.metadata?.expected_date || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Subir XML de compra</h2>
        <p className="mt-1 text-xs text-slate-500">Puedes seleccionar varios archivos a la vez (carga masiva) — duplicados se saltan sin detener el resto.</p>
        <input className="input mt-3" type="file" accept=".xml" multiple onChange={(e) => handleFiles(e.target.files)} />
        {fileNames.length > 0 && <p className="mt-1 text-xs text-slate-500">{fileNames.length === 1 ? fileNames[0] : `${fileNames.length} archivos seleccionados`}</p>}

        {xml && pendingOrders.length > 0 && (
          <label className="mt-3 block">
            <span className="label">¿Concilia con una orden pendiente? (opcional)</span>
            <select className="input" value={poReference} onChange={(e) => setPoReference(e.target.value)}>
              <option value="">No, es una compra nueva</option>
              {pendingOrders.map((row) => (
                <option key={row.id} value={row.source_id}>
                  {row.source_id} — {row.party_legal_name_snapshot}
                </option>
              ))}
            </select>
          </label>
        )}

        {xml && (
          <div className="mt-3 flex gap-2">
            <button className="btn-ghost px-4 py-2" disabled={busy} onClick={handlePreview}>
              Vista previa
            </button>
            <button className="btn-primary px-4 py-2" disabled={busy} onClick={handleImport}>
              Importar y sumar al kardex
            </button>
          </div>
        )}

        {xmls.length > 0 && (
          <div className="mt-3">
            <button className="btn-primary px-4 py-2" disabled={busy} onClick={handleBatchImport}>
              Importar los {xmls.length} archivos
            </button>
          </div>
        )}

        {preview && (
          <div className="mt-4 rounded-md border border-slate-200 p-3 text-sm">
            <p>
              <span className="font-semibold">{preview.nombre_emisor}</span> ({preview.rfc_emisor}) — Total ${preview.total}
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-600">
              {preview.items.map((item, i) => (
                <li key={i}>
                  {item.descripcion} — {item.cantidad} pza, clave SAT {item.clave_prod_serv} ({item.clave_unidad})
                </li>
              ))}
            </ul>
          </div>
        )}

        {imported && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <p className="font-semibold">Movimientos creados:</p>
            <ul className="mt-2 space-y-1 text-xs">
              {imported.items.map((item, i) => (
                <li key={i}>
                  +{item.cantidad} {item.descripcion} (clave SAT {item.sat_product_key}) {item.product_created ? "— producto nuevo" : "— producto existente"}
                </li>
              ))}
            </ul>
          </div>
        )}

        {batchResult && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <p className="font-semibold">
              Lote procesado: {batchResult.imported} importadas, {batchResult.skipped_duplicates} ya existían, {batchResult.failed} fallaron (de {batchResult.total}).
            </p>
            {batchResult.failed_items.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-red-700">
                {batchResult.failed_items.map((item) => (
                  <li key={item.index}>
                    Archivo #{item.index + 1}: {item.error} {item.detail ? `— ${item.detail}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Facturas de compra importadas</h2>
        {invoices.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Todavía no hay facturas de compra importadas.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Proveedor</th><th>Total</th><th>UUID</th><th>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">
                      {row.party_legal_name_snapshot}
                      <div className="text-xs text-slate-400">{row.party_rfc_snapshot}</div>
                    </td>
                    <td>${row.total}</td>
                    <td className="max-w-[160px] truncate text-xs text-slate-500">{row.uuid}</td>
                    <td className="text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
