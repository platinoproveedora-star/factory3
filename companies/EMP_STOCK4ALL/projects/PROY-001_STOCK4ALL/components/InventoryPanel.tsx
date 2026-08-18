"use client";

import { useEffect, useMemo, useState, FormEvent, ChangeEvent } from "react";

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

/** Selector de almacen (ya existentes + crear nuevo). Se usa igual arriba
 * en el header y dentro del borrador -- ambos comparten el mismo estado
 * para que sean, literalmente, el mismo selector. */
function WarehousePicker({
  warehouses,
  value,
  onChange,
  adding,
  setAdding,
  newCode,
  setNewCode,
  newName,
  setNewName,
  onCreate
}: {
  warehouses: Warehouse[];
  value: string;
  onChange: (value: string) => void;
  adding: boolean;
  setAdding: (value: boolean) => void;
  newCode: string;
  setNewCode: (value: string) => void;
  newName: string;
  setNewName: (value: string) => void;
  onCreate: () => void;
}) {
  if (adding) {
    return (
      <div className="flex items-center gap-1">
        <input className="input w-24" placeholder="Codigo" value={newCode} onChange={(e) => setNewCode(e.target.value)} />
        <input className="input w-40" placeholder="Nombre" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="button" className="btn-primary px-3 text-xs" onClick={onCreate}>
          Crear
        </button>
        <button type="button" className="btn-ghost px-2 text-xs" onClick={() => setAdding(false)}>
          x
        </button>
      </div>
    );
  }
  return (
    <select
      className="input w-auto"
      value={value}
      onChange={(event) => {
        if (event.target.value === "__new__") setAdding(true);
        else onChange(event.target.value);
      }}
    >
      {warehouses.map((warehouse) => (
        <option key={warehouse.id} value={warehouse.code}>
          {warehouse.name} ({warehouse.code})
        </option>
      ))}
      <option value="__new__">+ Nuevo almacen...</option>
    </select>
  );
}

/** Select de producto del catalogo + opcion de dar de alta uno nuevo sin
 * salir del renglon (util cuando el documento trae productos que todavia
 * no existen, ej. la primera compra de una categoria nueva). */
function ProductPicker({
  stock,
  value,
  onChange,
  prefillName,
  prefillSku,
  onProductCreated
}: {
  stock: StockRow[];
  value: string;
  onChange: (productId: string) => void;
  prefillName: string;
  prefillSku: string;
  onProductCreated: () => Promise<void>;
}) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState(prefillName);
  const [sku, setSku] = useState(prefillSku);
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim()) return;
    setSaving(true);
    setLocalError(null);
    try {
      const res = await fetch("/api/inventory/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_name: name, sku, unit: "pieza" })
      });
      const json = await res.json();
      if (!json.ok) {
        setLocalError(json.error || "error creando producto");
        return;
      }
      await onProductCreated();
      onChange(json.data.product.id);
      setCreating(false);
    } finally {
      setSaving(false);
    }
  }

  if (creating) {
    return (
      <div className="grid gap-1">
        <input className="input" placeholder="Nombre del producto" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="flex gap-1">
          <input className="input" placeholder="SKU" value={sku} onChange={(e) => setSku(e.target.value)} />
          <button type="button" disabled={saving} className="btn-primary px-2 text-xs" onClick={handleCreate}>
            Crear
          </button>
          <button type="button" className="btn-ghost px-2 text-xs" onClick={() => setCreating(false)}>
            x
          </button>
        </div>
        {localError && <p className="text-xs text-red-600">{localError}</p>}
      </div>
    );
  }

  return (
    <select
      className="input"
      value={value}
      onChange={(event) => {
        if (event.target.value === "__new__") setCreating(true);
        else onChange(event.target.value);
      }}
    >
      <option value="">Selecciona...</option>
      {stock.map((row) => (
        <option key={row.product_id} value={row.product_id}>
          {row.product_name} {row.sku ? `(${row.sku})` : ""}
        </option>
      ))}
      <option value="__new__">+ Nuevo producto...</option>
    </select>
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

type DraftItem = PurchaseItem & { producto_texto: string; unidad_texto: string; sku_texto: string };
type PurchaseDraft = {
  id: string;
  file_name: string | null;
  file_url: string | null;
  status: string;
  supplier_name_hint: string | null;
  extracted_json: any;
  created_at: string;
};

function draftItemsFromExtracted(extracted: any): DraftItem[] {
  const items = Array.isArray(extracted?.items) ? extracted.items : [];
  if (!items.length) return [{ ...emptyPurchaseItem(), producto_texto: "", unidad_texto: "", sku_texto: "" }];
  return items.map((item: any) => ({
    product_id: item.product_id || "",
    lot_code: item.lot_code || "",
    quantity: item.quantity != null ? String(item.quantity) : item.cantidad != null ? String(item.cantidad) : "",
    unit_cost: item.unit_cost != null ? String(item.unit_cost) : item.costo_unitario != null ? String(item.costo_unitario) : "",
    tax_rate: item.tax_rate != null ? String(item.tax_rate) : "0.16",
    notes: item.notes || "",
    producto_texto: item.producto_texto || item.producto || "",
    unidad_texto: item.unidad_texto || item.unidad || "",
    sku_texto: item.sku_texto || item.sku || ""
  }));
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = () => reject(new Error("no se pudo leer el archivo"));
    reader.readAsDataURL(file);
  });
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
  const [tab, setTab] = useState<"stock" | "producto" | "compra" | "compra_archivo">("stock");

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

  const [drafts, setDrafts] = useState<PurchaseDraft[]>([]);
  const [uploading, setUploading] = useState(false);
  const [activeDraft, setActiveDraft] = useState<PurchaseDraft | null>(null);
  const [draftItems, setDraftItems] = useState<DraftItem[]>([]);
  const [dSupplierId, setDSupplierId] = useState("");
  const [dMovementDate, setDMovementDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [dExternalFolio, setDExternalFolio] = useState("");
  const [dPaidAmount, setDPaidAmount] = useState("0");
  const [dNotes, setDNotes] = useState("");

  async function loadDrafts() {
    try {
      const res = await fetch("/api/inventory/purchase-drafts", { cache: "no-store" });
      const json = await res.json();
      if (json.ok) setDrafts((json.data.drafts || []).filter((d: PurchaseDraft) => d.status === "draft"));
    } catch {
      // silencioso
    }
  }

  function openDraft(draft: PurchaseDraft) {
    setActiveDraft(draft);
    const extracted = draft.extracted_json || {};
    setDraftItems(draftItemsFromExtracted(extracted));
    setDSupplierId(extracted.supplier_id || "");
    setDMovementDate(extracted.fecha || new Date().toISOString().slice(0, 10));
    setDExternalFolio(extracted.folio_proveedor || "");
    setDPaidAmount(String(extracted.paid_amount || 0));
    setDNotes(extracted.notes || "");
  }

  function closeDraft() {
    setActiveDraft(null);
    setDraftItems([]);
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      setError("Archivo demasiado grande (max 4MB)");
      return;
    }
    setError(null);
    setNotice(null);
    setUploading(true);
    try {
      const content_b64 = await fileToBase64(file);
      const res = await fetch("/api/inventory/purchase-drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_b64, media_type: file.type, filename: file.name })
      });
      const json = await res.json();
      if (!json.ok) {
        setError(json.error || "error subiendo/leyendo el archivo");
        return;
      }
      setNotice("Archivo leido. Revisa la tabla antes de confirmar.");
      await loadDrafts();
      openDraft(json.data.draft);
    } catch (err: any) {
      setError(err.message || "error subiendo archivo");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDraft(id: string) {
    const res = await fetch(`/api/inventory/purchase-drafts/${id}`, { method: "DELETE" });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error borrando borrador");
      return;
    }
    if (activeDraft?.id === id) closeDraft();
    loadDrafts();
  }

  function updateDraftItem(index: number, patch: Partial<DraftItem>) {
    setDraftItems((items) => items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  function addDraftItem() {
    setDraftItems((items) => [...items, { ...emptyPurchaseItem(), producto_texto: "", unidad_texto: "", sku_texto: "" }]);
  }

  function removeDraftItem(index: number) {
    setDraftItems((items) => (items.length > 1 ? items.filter((_, i) => i !== index) : items));
  }

  function buildExtractedJson() {
    return {
      supplier_id: dSupplierId,
      fecha: dMovementDate,
      folio_proveedor: dExternalFolio,
      paid_amount: Number(dPaidAmount || 0),
      notes: dNotes,
      items: draftItems
    };
  }

  async function handleSaveDraft() {
    if (!activeDraft) return;
    setError(null);
    setNotice(null);
    const res = await fetch(`/api/inventory/purchase-drafts/${activeDraft.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ extracted_json: buildExtractedJson() })
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error guardando borrador");
      return;
    }
    setNotice("Borrador guardado");
    loadDrafts();
  }

  async function handleConfirmDraft() {
    if (!activeDraft) return;
    setError(null);
    setNotice(null);
    const items = draftItems
      .filter((item) => item.product_id && Number(item.quantity) > 0)
      .map((item) => ({
        product_id: item.product_id,
        lot_code: item.lot_code || undefined,
        quantity: Number(item.quantity),
        unit_cost: Number(item.unit_cost || 0),
        tax_rate: Number(item.tax_rate),
        notes: item.notes || undefined
      }));
    if (!items.length || !dSupplierId) {
      setError("Selecciona proveedor y asigna producto a cada renglon antes de ingresar la compra");
      return;
    }
    const res = await fetch(`/api/inventory/purchase-drafts/${activeDraft.id}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        supplier_id: dSupplierId,
        movement_date: dMovementDate,
        external_folio: dExternalFolio || undefined,
        paid_amount: Number(dPaidAmount || 0),
        notes: dNotes || undefined,
        warehouse_id: warehouseId,
        items
      })
    });
    const json = await res.json();
    if (!json.ok) {
      setError(json.error || "error registrando compra");
      return;
    }
    setNotice(`Compra ${json.data.purchase.source_folio} registrada (${money(json.data.purchase.total_cost)})`);
    closeDraft();
    loadDrafts();
    loadStock();
  }

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
    loadDrafts();
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
          <WarehousePicker
            warehouses={warehouses}
            value={warehouseId}
            onChange={setWarehouseId}
            adding={addingWarehouse}
            setAdding={setAddingWarehouse}
            newCode={newWarehouseCode}
            setNewCode={setNewWarehouseCode}
            newName={newWarehouseName}
            setNewName={setNewWarehouseName}
            onCreate={handleCreateWarehouse}
          />
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
          { id: "compra", label: "Registrar compra" },
          { id: "compra_archivo", label: "Compra con Archivo" }
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

      {tab === "compra_archivo" && (
        <div className="mt-4 grid gap-4">
          <div className="card">
            <label className="label">Subir documento de compra (PDF, imagen o Excel)</label>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls"
              disabled={uploading}
              onChange={handleFileUpload}
              className="input"
            />
            {uploading && <p className="mt-2 text-xs text-muted">Subiendo y leyendo con IA...</p>}
          </div>

          {!!drafts.length && (
            <div className="card">
              <p className="label">Borradores pendientes</p>
              <ul className="grid gap-2">
                {drafts.map((draft) => (
                  <li key={draft.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                    <div>
                      <p className="font-medium text-ink">{draft.file_name || "documento"}</p>
                      <p className="text-xs text-muted">
                        {draft.supplier_name_hint || "sin proveedor"} · {new Date(draft.created_at).toLocaleDateString("es-MX")}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button type="button" className="btn-ghost px-2 text-xs" onClick={() => openDraft(draft)}>
                        Editar
                      </button>
                      <button type="button" className="btn-ghost px-2 text-xs" onClick={() => handleDeleteDraft(draft.id)}>
                        Borrar
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {activeDraft && (
            <div className="card grid gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="label mb-0">Archivo</p>
                  <a href={activeDraft.file_url || "#"} target="_blank" rel="noreferrer" className="text-sm text-steel underline">
                    {activeDraft.file_name}
                  </a>
                </div>
                <button type="button" className="btn-ghost px-3 text-xs" onClick={() => handleDeleteDraft(activeDraft.id)}>
                  Quitar archivo
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="col-span-2">
                  <label className="label">Proveedor</label>
                  <select required className="input" value={dSupplierId} onChange={(e) => setDSupplierId(e.target.value)}>
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
                  <input type="date" className="input" value={dMovementDate} onChange={(e) => setDMovementDate(e.target.value)} />
                </div>
                <div>
                  <label className="label">Folio proveedor</label>
                  <input className="input" value={dExternalFolio} onChange={(e) => setDExternalFolio(e.target.value)} />
                </div>
              </div>

              <div className="overflow-x-auto">
                <p className="text-xs text-muted">Tabla preliminar leida del documento. Revisa y asigna el producto real de tu catalogo en cada renglon.</p>
                <table className="mt-2 w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase text-muted">
                      <th className="py-1">Leido del documento</th>
                      <th>SKU / clave proveedor</th>
                      <th>Producto (catalogo)</th>
                      <th>Lote</th>
                      <th>Cantidad</th>
                      <th>Costo unit.</th>
                      <th>IVA</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {draftItems.map((item, index) => (
                      <tr key={index}>
                        <td className="py-1 pr-2 text-xs text-muted">
                          {item.producto_texto} {item.unidad_texto ? `(${item.unidad_texto})` : ""}
                        </td>
                        <td className="pr-2 text-xs text-muted">{item.sku_texto || "-"}</td>
                        <td className="pr-2">
                          <ProductPicker
                            stock={stock}
                            value={item.product_id}
                            onChange={(productId) => updateDraftItem(index, { product_id: productId })}
                            prefillName={item.producto_texto}
                            prefillSku={item.sku_texto}
                            onProductCreated={loadStock}
                          />
                        </td>
                        <td className="pr-2">
                          <input className="input" value={item.lot_code} onChange={(e) => updateDraftItem(index, { lot_code: e.target.value })} />
                        </td>
                        <td className="pr-2">
                          <input
                            type="number"
                            step="0.01"
                            className="input"
                            value={item.quantity}
                            onChange={(e) => updateDraftItem(index, { quantity: e.target.value })}
                          />
                        </td>
                        <td className="pr-2">
                          <input
                            type="number"
                            step="0.01"
                            className="input"
                            value={item.unit_cost}
                            onChange={(e) => updateDraftItem(index, { unit_cost: e.target.value })}
                          />
                        </td>
                        <td className="pr-2">
                          <select className="input" value={item.tax_rate} onChange={(e) => updateDraftItem(index, { tax_rate: e.target.value })}>
                            {TAX_RATES.map((rate) => (
                              <option key={rate.value} value={rate.value}>
                                {rate.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <button type="button" className="btn-ghost px-2 text-xs" onClick={() => removeDraftItem(index)}>
                            Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button type="button" className="btn-ghost mt-2 px-3 py-1 text-xs" onClick={addDraftItem}>
                  + Agregar renglon
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div>
                  <label className="label">Pagado</label>
                  <input type="number" step="0.01" className="input" value={dPaidAmount} onChange={(e) => setDPaidAmount(e.target.value)} />
                </div>
                <div className="col-span-2">
                  <label className="label">Notas</label>
                  <input className="input" value={dNotes} onChange={(e) => setDNotes(e.target.value)} />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="label mb-0">Almacen</label>
                <WarehousePicker
                  warehouses={warehouses}
                  value={warehouseId}
                  onChange={setWarehouseId}
                  adding={addingWarehouse}
                  setAdding={setAddingWarehouse}
                  newCode={newWarehouseCode}
                  setNewCode={setNewWarehouseCode}
                  newName={newWarehouseName}
                  setNewName={setNewWarehouseName}
                  onCreate={handleCreateWarehouse}
                />
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn-ghost px-4 py-2" onClick={handleSaveDraft}>
                  Guardar borrador
                </button>
                <button type="button" className="btn-primary px-4 py-2" onClick={handleConfirmDraft}>
                  Ingresar compra
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
