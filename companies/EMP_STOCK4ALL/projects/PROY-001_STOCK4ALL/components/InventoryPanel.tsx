"use client";

import { useEffect, useState, FormEvent } from "react";

type StockRow = {
  product_id: string;
  folio: string;
  product_name: string;
  sku: string | null;
  category: string | null;
  unit: string;
  quantity: number;
  min_stock: number;
  stock_status: "ok" | "bajo" | "negativo";
  avg_cost: number;
  estimated_value: number;
};

type Party = { id: string; party_name: string; party_type: string };

const WAREHOUSES = [{ id: "PRINCIPAL", label: "Principal" }];

function money(value: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(value || 0));
}

function qty(value: number) {
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(Number(value || 0));
}

function statusLabel(status: string) {
  if (status === "negativo") return { text: "Negativo", className: "text-red-600" };
  if (status === "bajo") return { text: "Bajo minimo", className: "text-amber-600" };
  return { text: "OK", className: "text-emerald-600" };
}

export default function InventoryPanel() {
  const [warehouseId, setWarehouseId] = useState("PRINCIPAL");
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive">("active");
  const [stock, setStock] = useState<StockRow[]>([]);
  const [summary, setSummary] = useState<{ products: number; low_stock: number; negative_stock: number; estimated_value: number } | null>(null);
  const [suppliers, setSuppliers] = useState<Party[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tab, setTab] = useState<"stock" | "producto" | "compra">("stock");

  async function loadStock(status: "active" | "inactive" = statusFilter) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/inventory/stock?status=${status}`, { cache: "no-store" });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "error cargando stock");
      setStock(json.data.stock || []);
      setSummary(json.data.summary || null);
    } catch (err: any) {
      setError(err.message || "error cargando stock");
    } finally {
      setLoading(false);
    }
  }

  function handleStatusChange(next: "active" | "inactive") {
    setStatusFilter(next);
    loadStock(next);
  }

  async function loadParties() {
    try {
      const res = await fetch("/api/inventory/parties", { cache: "no-store" });
      const json = await res.json();
      if (json.ok) setSuppliers(json.data.suppliers || []);
    } catch {
      // silencioso: el formulario de compra igual funciona sin catalogo de proveedores
    }
  }

  useEffect(() => {
    loadStock();
    loadParties();
  }, []);

  async function handleNewProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const form = new FormData(event.currentTarget);
    const body = {
      product_name: String(form.get("product_name") || ""),
      sku: String(form.get("sku") || ""),
      category: String(form.get("category") || ""),
      unit: String(form.get("unit") || "pieza"),
      min_stock: Number(form.get("min_stock") || 0)
    };
    const res = await fetch("/api/inventory/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error guardando producto");
      return;
    }
    setNotice(`Producto ${json.data.product.folio} creado`);
    event.currentTarget.reset();
    loadStock();
  }

  async function handlePurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const form = new FormData(event.currentTarget);
    const body = {
      source_type: "compra",
      product_id: String(form.get("product_id") || ""),
      party_id: String(form.get("party_id") || ""),
      quantity: Number(form.get("quantity") || 0),
      unit_cost: Number(form.get("unit_cost") || 0),
      warehouse_id: warehouseId
    };
    const res = await fetch("/api/inventory/kardex", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error registrando compra");
      return;
    }
    setNotice(`Compra ${json.data.movement.folio} registrada`);
    event.currentTarget.reset();
    loadStock();
  }

  return (
    <div className="mx-auto max-w-7xl px-5 py-6">
      <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Stock4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Inventario</h1>
        </div>
        <div className="flex items-center gap-2">
          <label className="label mb-0">Almacen</label>
          <select
            className="input w-auto"
            value={warehouseId}
            onChange={(event) => setWarehouseId(event.target.value)}
          >
            {WAREHOUSES.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.label}
              </option>
            ))}
          </select>
          <label className="label mb-0">Ver</label>
          <select
            className="input w-auto"
            value={statusFilter}
            onChange={(event) => handleStatusChange(event.target.value as "active" | "inactive")}
          >
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </select>
        </div>
      </section>

      {summary && (
        <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="card">
            <p className="text-xs text-muted">Productos</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{summary.products}</p>
          </div>
          <div className="card">
            <p className="text-xs text-muted">Bajo minimo</p>
            <p className="mt-1 text-2xl font-semibold text-amber-600">{summary.low_stock}</p>
          </div>
          <div className="card">
            <p className="text-xs text-muted">Negativo</p>
            <p className="mt-1 text-2xl font-semibold text-red-600">{summary.negative_stock}</p>
          </div>
          <div className="card">
            <p className="text-xs text-muted">Valor estimado</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{money(summary.estimated_value)}</p>
          </div>
        </section>
      )}

      {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {notice && <p className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</p>}

      <nav className="mt-6 flex gap-2 border-b border-border">
        {[
          { id: "stock", label: "Stock" },
          { id: "producto", label: "Nuevo producto" },
          { id: "compra", label: "Registrar compra" }
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id as typeof tab)}
            className={`px-3 py-2 text-sm font-medium ${tab === item.id ? "border-b-2 border-moss text-moss" : "text-muted"}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === "stock" && (
        <div className="card mt-4 overflow-x-auto">
          {loading ? (
            <p className="text-sm text-muted">Cargando...</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase text-muted">
                  <th className="py-2">Folio</th>
                  <th>Producto</th>
                  <th>SKU</th>
                  <th>Categoria</th>
                  <th>Cantidad</th>
                  <th>Estado</th>
                  <th>Costo prom.</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {stock.map((row) => {
                  const status = statusLabel(row.stock_status);
                  return (
                    <tr key={row.product_id} className="border-b border-border/60">
                      <td className="py-2">{row.folio}</td>
                      <td>{row.product_name}</td>
                      <td>{row.sku || "-"}</td>
                      <td>{row.category || "-"}</td>
                      <td>
                        {qty(row.quantity)} {row.unit}
                      </td>
                      <td className={status.className}>{status.text}</td>
                      <td>{money(row.avg_cost)}</td>
                      <td>{money(row.estimated_value)}</td>
                    </tr>
                  );
                })}
                {!stock.length && (
                  <tr>
                    <td colSpan={8} className="py-6 text-center text-muted">
                      Sin productos todavia.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "producto" && (
        <form onSubmit={handleNewProduct} className="card mt-4 grid max-w-xl gap-3">
          <div>
            <label className="label">Nombre del producto</label>
            <input name="product_name" required className="input" placeholder="Tuberia PVC 4 pulgadas" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">SKU / codigo</label>
              <input name="sku" className="input" />
            </div>
            <div>
              <label className="label">Categoria</label>
              <input name="category" className="input" placeholder="tuberia" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Unidad</label>
              <input name="unit" className="input" defaultValue="pieza" />
            </div>
            <div>
              <label className="label">Stock minimo (alerta)</label>
              <input name="min_stock" type="number" step="0.01" className="input" defaultValue={0} />
            </div>
          </div>
          <button type="submit" className="btn-primary px-4 py-2">
            Guardar producto
          </button>
        </form>
      )}

      {tab === "compra" && (
        <form onSubmit={handlePurchase} className="card mt-4 grid max-w-xl gap-3">
          <div>
            <label className="label">Producto</label>
            <select name="product_id" required className="input">
              <option value="">Selecciona un producto</option>
              {stock.map((row) => (
                <option key={row.product_id} value={row.product_id}>
                  {row.product_name} {row.sku ? `(${row.sku})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Proveedor</label>
            <select name="party_id" required className="input">
              <option value="">Selecciona un proveedor</option>
              {suppliers.map((party) => (
                <option key={party.id} value={party.id}>
                  {party.party_name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Cantidad</label>
              <input name="quantity" type="number" step="0.01" required className="input" />
            </div>
            <div>
              <label className="label">Costo unitario</label>
              <input name="unit_cost" type="number" step="0.01" required className="input" />
            </div>
          </div>
          <p className="text-xs text-muted">Almacen: {warehouseId}</p>
          <button type="submit" className="btn-primary px-4 py-2">
            Registrar compra
          </button>
        </form>
      )}
    </div>
  );
}
