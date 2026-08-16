"use client";

import { useEffect, useState } from "react";

type Product = {
  id: string;
  source_product_key: string;
  fiscal_product_name: string;
  sat_product_key: string;
  sat_unit_key: string;
  tax_object?: string;
  iva_rate: number;
  status: string;
  classification_group?: string;
  classification_source?: string;
  stock?: { sandbox?: number; production?: number };
};

const CLASSIFICATION_OPTIONS = [
  { value: "mercancia", label: "Mercancía (mueve inventario)" },
  { value: "gasto_general", label: "Gasto general" },
  { value: "activo_fijo", label: "Activo fijo / inversión" },
  { value: "servicio", label: "Servicio" },
  { value: "otro", label: "Otro" },
];

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

const empty = { source_product_key: "", fiscal_product_name: "", sat_product_key: "", sat_unit_key: "", tax_object: "02", iva_rate: 0.16 };

export default function ProductsForm() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [form, setForm] = useState(empty);

  async function refresh() {
    setLoading(true);
    const res = await api<{ products: Product[] }>("/api/factu4all/products");
    setProducts(res.data?.products || []);
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando...");
    const res = await api("/api/factu4all/products", { method: "POST", body: JSON.stringify(form) });
    setMessage(res.ok ? "Guardado." : `Error: ${res.error}`);
    if (res.ok) {
      setForm(empty);
      refresh();
    }
  }

  async function markReady(sourceProductKey: string) {
    setBusyKey(sourceProductKey);
    const res = await api("/api/factu4all/products", { method: "POST", body: JSON.stringify({ source_product_key: sourceProductKey, status: "ready" }) });
    if (!res.ok) setMessage(res.error || "Error al actualizar");
    setBusyKey(null);
    refresh();
  }

  async function setClassification(sourceProductKey: string, classificationGroup: string) {
    setBusyKey(sourceProductKey);
    const res = await api("/api/factu4all/products", {
      method: "POST",
      body: JSON.stringify({ source_product_key: sourceProductKey, classification_group: classificationGroup, classification_source: "manual" }),
    });
    if (!res.ok) setMessage(res.error || "Error al clasificar");
    setBusyKey(null);
    refresh();
  }

  const pendingReview = products.filter((p) => p.classification_source === "pending_review" || !p.classification_group);

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Nuevo producto fiscal</h2>
        <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="label">Clave / SKU origen</span>
            <input className="input" required value={form.source_product_key} onChange={(e) => setForm({ ...form, source_product_key: e.target.value })} />
          </label>
          <label className="block sm:col-span-2">
            <span className="label">Nombre fiscal</span>
            <input className="input" required value={form.fiscal_product_name} onChange={(e) => setForm({ ...form, fiscal_product_name: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Clave SAT</span>
            <input className="input" required value={form.sat_product_key} onChange={(e) => setForm({ ...form, sat_product_key: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Unidad SAT</span>
            <input className="input" required value={form.sat_unit_key} onChange={(e) => setForm({ ...form, sat_unit_key: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Objeto de impuesto</span>
            <input className="input" value={form.tax_object} onChange={(e) => setForm({ ...form, tax_object: e.target.value })} />
          </label>
          <div className="sm:col-span-3">
            <button className="btn-primary px-4 py-2" type="submit">Guardar (status: revisar)</button>
          </div>
        </form>
      </section>

      {pendingReview.length > 0 && (
        <section className="card border-amber-300 bg-amber-50">
          <h2 className="text-sm font-semibold uppercase text-amber-700">Sin clasificar ({pendingReview.length})</h2>
          <p className="mt-1 text-xs text-amber-700">
            El sistema no pudo inferir automáticamente si estos conceptos son mercancía, gasto general, activo fijo o servicio. Mientras no se clasifiquen, no afectan inventario.
          </p>
          <div className="mt-3 space-y-2">
            {pendingReview.map((row) => (
              <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-amber-200 bg-white p-2 text-sm">
                <div>
                  {row.fiscal_product_name}
                  <div className="text-xs text-slate-400">{row.source_product_key} · clave SAT {row.sat_product_key || "—"}</div>
                </div>
                <select
                  className="input w-56"
                  disabled={busyKey === row.source_product_key}
                  value=""
                  onChange={(e) => e.target.value && setClassification(row.source_product_key, e.target.value)}
                >
                  <option value="">Clasificar como...</option>
                  {CLASSIFICATION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="card">
        {loading ? (
          <p className="text-sm text-slate-500">Cargando...</p>
        ) : products.length === 0 ? (
          <p className="text-sm text-slate-500">Todavía no hay productos fiscales.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Clave origen</th><th>Nombre fiscal</th><th>Clave SAT</th><th>Unidad SAT</th><th>Clasificación</th><th>Estado</th><th>Stock sandbox</th><th>Stock producción</th><th></th>
                </tr>
              </thead>
              <tbody>
                {products.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.source_product_key}</td>
                    <td>{row.fiscal_product_name}</td>
                    <td>{row.sat_product_key || "—"}</td>
                    <td>{row.sat_unit_key || "—"}</td>
                    <td className="text-xs">
                      {row.classification_group || "—"}
                      {row.classification_source && <div className="text-xs text-slate-400">{row.classification_source}</div>}
                    </td>
                    <td>{row.status}</td>
                    <td className={Number(row.stock?.sandbox || 0) < 0 ? "text-amber-600" : ""}>{row.stock?.sandbox ?? 0}</td>
                    <td className={Number(row.stock?.production || 0) < 0 ? "text-amber-600" : ""}>{row.stock?.production ?? 0}</td>
                    <td>
                      {row.status !== "ready" && (
                        <button className="btn-ghost px-3 py-1 text-xs" disabled={busyKey === row.source_product_key} onClick={() => markReady(row.source_product_key)}>
                          Marcar ready
                        </button>
                      )}
                    </td>
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
