"use client";

import { useEffect, useMemo, useState, FormEvent } from "react";

type StockRow = {
  product_id: string;
  folio: string;
  product_key: string | null;
  product_name: string;
  sku: string | null;
  category: string | null;
  category_2: string | null;
  brand: string | null;
  unit: string;
  quantity: number;
  min_stock: number;
  stock_status: "ok" | "bajo" | "negativo";
  avg_cost: number;
  estimated_value: number;
};

function uniqueSorted(values: (string | null | undefined)[]): string[] {
  const set = new Set(values.map((v) => (v || "").trim()).filter(Boolean));
  return Array.from(set).sort((a, b) => a.localeCompare(b, "es"));
}

/** Select con catalogo de valores ya capturados + opcion de escribir uno nuevo. */
function CatalogSelect({
  label,
  options,
  value,
  onChange,
  placeholder
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [customMode, setCustomMode] = useState(false);

  if (customMode) {
    return (
      <div>
        <label className="label">{label}</label>
        <div className="flex gap-2">
          <input
            className="input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder={placeholder}
            autoFocus
          />
          <button
            type="button"
            className="btn-ghost px-3 text-xs"
            onClick={() => {
              setCustomMode(false);
              onChange("");
            }}
          >
            Lista
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label className="label">{label}</label>
      <select
        className="input"
        value={value}
        onChange={(event) => {
          if (event.target.value === "__new__") {
            setCustomMode(true);
            onChange("");
          } else {
            onChange(event.target.value);
          }
        }}
      >
        <option value="">Selecciona...</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
        <option value="__new__">+ Nueva...</option>
      </select>
    </div>
  );
}

type Party = { id: string; party_name: string; party_type: string };
type Warehouse = { id: string; code: string; name: string; is_default: boolean };
type PurchaseItem = { product_id: string; lot_code: string; quantity: string; unit_cost: string; tax_rate: string; notes: string };

const TAX_RATES = [
  { value: "0", label: "IVA 0%" },
  { value: "0.08", label: "IVA 8%" },
  { value: "0.16", label: "IVA 16%" }
];

function emptyPurchaseItem(): PurchaseItem {
  return { product_id: "", lot_code: "", quantity: "", unit_cost: "", tax_rate: "0.16", notes: "" };
}

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
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [warehouseId, setWarehouseId] = useState("");
  const [addingWarehouse, setAddingWarehouse] = useState(false);
  const [newWarehouseCode, setNewWarehouseCode] = useState("");
  const [newWarehouseName, setNewWarehouseName] = useState("");
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive">("active");
  const [stock, setStock] = useState<StockRow[]>([]);
  const [summary, setSummary] = useState<{ products: number; low_stock: number; negative_stock: number; estimated_value: number } | null>(null);
  const [suppliers, setSuppliers] = useState<Party[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tab, setTab] = useState<"stock" | "producto" | "compra">("stock");

  const [npName, setNpName] = useState("");
  const [npKey, setNpKey] = useState("");
  const [npSku, setNpSku] = useState("");
  const [npCategory, setNpCategory] = useState("");
  const [npCategory2, setNpCategory2] = useState("");
  const [npBrand, setNpBrand] = useState("");
  const [npUnit, setNpUnit] = useState("pieza");
  const [npMinStock, setNpMinStock] = useState("0");

  const [pSupplierId, setPSupplierId] = useState("");
  const [pMovementDate, setPMovementDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [pExternalFolio, setPExternalFolio] = useState("");
  const [pPaidAmount, setPPaidAmount] = useState("0");
  const [pNotes, setPNotes] = useState("");
  const [purchaseItems, setPurchaseItems] = useState<PurchaseItem[]>([emptyPurchaseItem()]);

  function updatePurchaseItem(index: number, patch: Partial<PurchaseItem>) {
    setPurchaseItems((items) => items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  function addPurchaseItem() {
    setPurchaseItems((items) => [...items, emptyPurchaseItem()]);
  }

  function removePurchaseItem(index: number) {
    setPurchaseItems((items) => (items.length > 1 ? items.filter((_, i) => i !== index) : items));
  }

  const purchaseTotal = useMemo(
    () =>
      purchaseItems.reduce((sum, item) => {
        const subtotal = Number(item.quantity || 0) * Number(item.unit_cost || 0);
        return sum + subtotal * (1 + Number(item.tax_rate || 0));
      }, 0),
    [purchaseItems]
  );

  const categoryOptions = useMemo(() => uniqueSorted(stock.map((r) => r.category)), [stock]);
  const category2Options = useMemo(() => uniqueSorted(stock.map((r) => r.category_2)), [stock]);
  const brandOptions = useMemo(() => uniqueSorted(stock.map((r) => r.brand)), [stock]);
  const unitOptions = useMemo(() => uniqueSorted(["pieza", ...stock.map((r) => r.unit)]), [stock]);

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

  async function loadWarehouses() {
    try {
      const res = await fetch("/api/inventory/warehouses", { cache: "no-store" });
      const json = await res.json();
      if (json.ok) {
        const list: Warehouse[] = json.data.warehouses || [];
        setWarehouses(list);
        setWarehouseId((current) => current || list.find((w) => w.is_default)?.code || list[0]?.code || "");
      }
    } catch {
      // silencioso: el default (ensure_default) igual se crea del lado del servidor
    }
  }

  async function handleCreateWarehouse() {
    if (!newWarehouseCode.trim() || !newWarehouseName.trim()) return;
    const res = await fetch("/api/inventory/warehouses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: newWarehouseCode.trim().toUpperCase(), name: newWarehouseName.trim() })
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error creando almacen");
      return;
    }
    setNewWarehouseCode("");
    setNewWarehouseName("");
    setAddingWarehouse(false);
    await loadWarehouses();
    setWarehouseId(json.data.warehouse.code);
  }

  useEffect(() => {
    loadStock();
    loadParties();
    loadWarehouses();
  }, []);

  async function handleNewProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const body = {
      product_name: npName,
      product_key: npKey,
      sku: npSku,
      category: npCategory,
      category_2: npCategory2,
      brand: npBrand,
      unit: npUnit || "pieza",
      min_stock: Number(npMinStock || 0)
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
    setNpName("");
    setNpKey("");
    setNpSku("");
    setNpCategory("");
    setNpCategory2("");
    setNpBrand("");
    setNpUnit("pieza");
    setNpMinStock("0");
    loadStock();
  }

  async function handlePurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const items = purchaseItems
      .filter((item) => item.product_id && Number(item.quantity) > 0)
      .map((item) => ({
        product_id: item.product_id,
        lot_code: item.lot_code || undefined,
        quantity: Number(item.quantity),
        unit_cost: Number(item.unit_cost || 0),
        tax_rate: Number(item.tax_rate),
        notes: item.notes || undefined
      }));
    if (!items.length) {
      setError("Agrega al menos un renglon con producto y cantidad");
      return;
    }
    const body = {
      supplier_id: pSupplierId,
      movement_date: pMovementDate,
      external_folio: pExternalFolio || undefined,
      paid_amount: Number(pPaidAmount || 0),
      notes: pNotes || undefined,
      warehouse_id: warehouseId,
      items
    };
    const res = await fetch("/api/inventory/purchases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error registrando compra");
      return;
    }
    setNotice(`Compra ${json.data.purchase.source_folio} registrada (${money(json.data.purchase.total_cost)})`);
    setPSupplierId("");
    setPExternalFolio("");
    setPPaidAmount("0");
    setPNotes("");
    setPurchaseItems([emptyPurchaseItem()]);
    loadStock();
  }

  return (
    <div className="mx-auto max-w-7xl px-5 py-6">
      <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Stock4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Inventario</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="label mb-0">Almacen</label>
          {!addingWarehouse ? (
            <select
              className="input w-auto"
              value={warehouseId}
              onChange={(event) => {
                if (event.target.value === "__new__") {
                  setAddingWarehouse(true);
                } else {
                  setWarehouseId(event.target.value);
                }
              }}
            >
              {warehouses.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.code}>
                  {warehouse.name} ({warehouse.code})
                </option>
              ))}
              <option value="__new__">+ Nuevo almacen...</option>
            </select>
          ) : (
            <div className="flex items-center gap-1">
              <input className="input w-24" placeholder="Codigo" value={newWarehouseCode} onChange={(e) => setNewWarehouseCode(e.target.value)} />
              <input className="input w-40" placeholder="Nombre" value={newWarehouseName} onChange={(e) => setNewWarehouseName(e.target.value)} />
              <button type="button" className="btn-primary px-3 text-xs" onClick={handleCreateWarehouse}>
                Crear
              </button>
              <button type="button" className="btn-ghost px-2 text-xs" onClick={() => setAddingWarehouse(false)}>
                x
              </button>
            </div>
          )}
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
          <p className="text-xs text-muted">Alta de catalogo. El folio se asigna solo (interno).</p>
          <div>
            <label className="label">Nombre</label>
            <input
              required
              className="input"
              placeholder="Tuberia PVC 4 pulgadas"
              value={npName}
              onChange={(event) => setNpName(event.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Clave interna</label>
              <input
                className="input"
                placeholder="La modifica el cliente"
                value={npKey}
                onChange={(event) => setNpKey(event.target.value)}
              />
            </div>
            <div>
              <label className="label">SKU</label>
              <input
                className="input"
                placeholder="Codigo de fabrica"
                value={npSku}
                onChange={(event) => setNpSku(event.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <CatalogSelect label="Categoria" options={categoryOptions} value={npCategory} onChange={setNpCategory} placeholder="tuberia" />
            <CatalogSelect label="Categoria 2" options={category2Options} value={npCategory2} onChange={setNpCategory2} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <CatalogSelect label="Marca" options={brandOptions} value={npBrand} onChange={setNpBrand} />
            <CatalogSelect label="Unidad" options={unitOptions} value={npUnit} onChange={setNpUnit} placeholder="pieza" />
          </div>
          <div>
            <label className="label">Minimo (alerta de stock bajo)</label>
            <input
              type="number"
              step="0.01"
              className="input"
              value={npMinStock}
              onChange={(event) => setNpMinStock(event.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary px-4 py-2">
            Guardar producto
          </button>
        </form>
      )}

      {tab === "compra" && (
        <form onSubmit={handlePurchase} className="card mt-4 grid gap-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="col-span-2">
              <label className="label">Proveedor</label>
              <select required className="input" value={pSupplierId} onChange={(e) => setPSupplierId(e.target.value)}>
                <option value="">Selecciona un proveedor</option>
                {suppliers.map((party) => (
                  <option key={party.id} value={party.id}>
                    {party.party_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Fecha</label>
              <input type="date" required className="input" value={pMovementDate} onChange={(e) => setPMovementDate(e.target.value)} />
            </div>
            <div>
              <label className="label">Folio proveedor</label>
              <input className="input" placeholder="Opcional" value={pExternalFolio} onChange={(e) => setPExternalFolio(e.target.value)} />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-muted">
                  <th className="py-1">Producto</th>
                  <th>Lote</th>
                  <th>Cantidad</th>
                  <th>Costo unit.</th>
                  <th>IVA</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {purchaseItems.map((item, index) => (
                  <tr key={index}>
                    <td className="py-1 pr-2">
                      <select
                        className="input"
                        value={item.product_id}
                        onChange={(e) => updatePurchaseItem(index, { product_id: e.target.value })}
                      >
                        <option value="">Selecciona...</option>
                        {stock.map((row) => (
                          <option key={row.product_id} value={row.product_id}>
                            {row.product_name} {row.sku ? `(${row.sku})` : ""}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="pr-2">
                      <input
                        className="input"
                        placeholder="GENERAL"
                        value={item.lot_code}
                        onChange={(e) => updatePurchaseItem(index, { lot_code: e.target.value })}
                      />
                    </td>
                    <td className="pr-2">
                      <input
                        type="number"
                        step="0.01"
                        className="input"
                        value={item.quantity}
                        onChange={(e) => updatePurchaseItem(index, { quantity: e.target.value })}
                      />
                    </td>
                    <td className="pr-2">
                      <input
                        type="number"
                        step="0.01"
                        className="input"
                        value={item.unit_cost}
                        onChange={(e) => updatePurchaseItem(index, { unit_cost: e.target.value })}
                      />
                    </td>
                    <td className="pr-2">
                      <select className="input" value={item.tax_rate} onChange={(e) => updatePurchaseItem(index, { tax_rate: e.target.value })}>
                        {TAX_RATES.map((rate) => (
                          <option key={rate.value} value={rate.value}>
                            {rate.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button type="button" className="btn-ghost px-2 text-xs" onClick={() => removePurchaseItem(index)}>
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button type="button" className="btn-ghost mt-2 px-3 py-1 text-xs" onClick={addPurchaseItem}>
              + Agregar renglon
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div>
              <label className="label">Pagado</label>
              <input type="number" step="0.01" className="input" value={pPaidAmount} onChange={(e) => setPPaidAmount(e.target.value)} />
            </div>
            <div className="col-span-2">
              <label className="label">Notas</label>
              <input className="input" value={pNotes} onChange={(e) => setPNotes(e.target.value)} />
            </div>
            <div className="flex flex-col justify-end">
              <p className="text-xs text-muted">Total estimado</p>
              <p className="text-lg font-semibold text-ink">{money(purchaseTotal)}</p>
            </div>
          </div>

          <p className="text-xs text-muted">Almacen: {warehouseId || "-"}</p>
          <button type="submit" className="btn-primary w-fit px-4 py-2">
            Registrar compra
          </button>
        </form>
      )}
    </div>
  );
}
