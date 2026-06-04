'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Boxes,
  Building2,
  CircleDollarSign,
  ClipboardList,
  PackagePlus,
  Pencil,
  Printer,
  RefreshCw,
  Save,
  Search,
  Store,
  Trash2,
  Truck,
  UserRoundPlus,
} from 'lucide-react';
import { loadDashboardData, type DashboardData } from '../lib/client-data';
import { money, qty, type KardexMovement, type Party, type Product } from '../lib/supabase';

type Tab = 'inventario' | 'producto' | 'kardex' | 'proveedores' | 'clientes' | 'ventas' | 'compras';
type RefreshFn = () => Promise<DashboardData | null>;

type RemisionDoc = {
  id: string;
  folio: string;
  external_folio: string | null;
  customer_name_snapshot: string | null;
  status: string;
  document_date: string;
  delivery_address: string | null;
  total: number;
  balance_total: number;
  notes: string | null;
  created_at: string;
};

type RemisionItem = {
  id: string;
  folio: string;
  product_id: string | null;
  inventory_product_id: string | null;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  lot_code: string | null;
  lot_cost_snapshot?: number | null;
  avg_cost_snapshot?: number | null;
  last_cost_snapshot?: number | null;
  tax_rate: number;
  tax_amount: number;
  line_total: number;
};

type RemisionDetail = {
  remision: RemisionDoc;
  items: RemisionItem[];
};

type MatrixData = {
  products: Array<{ id: string; folio: string; product_name: string; unit: string }>;
  rows: Array<{ id: string; folio: string; external_folio: string | null; customer_name_snapshot: string | null; document_date: string; products: Record<string, number>; row_total: number }>;
  totals: Record<string, number>;
  grand_total: number;
  start_date: string;
  end_date: string;
};

type PurchaseLine = {
  id: string;
  product_id: string;
  lot_code: string;
  quantity: string;
  unit_cost: string;
  tax_rate: string;
  notes: string;
};

type PurchaseSummary = {
  source_folio: string;
  external_folio: string | null;
  supplier_id: string | null;
  supplier_name_snapshot: string | null;
  movement_date: string;
  line_count: number;
  total_cost: number;
  paid_amount: number;
  balance_amount: number;
  payment_status: string;
  notes: string | null;
  items: KardexMovement[];
};

const emptyData: DashboardData = {
  products: [],
  customers: [],
  suppliers: [],
  purchases: [],
  sales: [],
  adjustments: [],
  stock: [],
  lot_stock: [],
  receivables_total: 0,
  payables_total: 0,
};

const tabs: Array<{ id: Tab; label: string; icon: any }> = [
  { id: 'inventario', label: 'Inventario', icon: Boxes },
  { id: 'producto', label: 'Producto', icon: PackagePlus },
  { id: 'kardex', label: 'Kardex', icon: ClipboardList },
  { id: 'proveedores', label: 'Proveedores', icon: Truck },
  { id: 'clientes', label: 'Clientes', icon: Store },
  { id: 'ventas', label: 'Ventas / salidas', icon: ArrowUpFromLine },
  { id: 'compras', label: 'Compras / entradas', icon: ArrowDownToLine },
];

function savedTab(): Tab {
  if (typeof window === 'undefined') return 'inventario';
  const value = window.localStorage.getItem('duralon_inventory_tab');
  if (tabs.some((tab) => tab.id === value)) return value as Tab;
  return 'inventario';
}

export default function InventoryDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('inventario');
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const nextData = await loadDashboardData();
      setData(nextData);
      return nextData;
    } catch (err: any) {
      setError(err.message || 'No se pudo cargar el dashboard');
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    setActiveTab(savedTab());
  }, []);

  useEffect(() => {
    window.localStorage.setItem('duralon_inventory_tab', activeTab);
  }, [activeTab]);

  const filteredProducts = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return data.products;
    return data.products.filter((p) =>
      [p.product_name, p.folio, p.sku, p.category].some((value) => String(value || '').toLowerCase().includes(term))
    );
  }, [data.products, search]);

  return (
    <main className="min-h-screen bg-[#f4f6f8]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white px-5 py-6 lg:block">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-slate-900 text-white">
            <Building2 size={20} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">EMP_DURALON</p>
            <h1 className="text-lg font-semibold text-slate-950">Inventario</h1>
          </div>
        </div>
        <nav className="mt-8 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const selected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id);
                  setNotice('');
                }}
                className={`flex w-full items-center gap-3 rounded px-3 py-2.5 text-left text-sm font-medium ${
                  selected ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                }`}
              >
                <Icon size={17} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="absolute bottom-6 left-5 right-5 rounded border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-700">Schema</p>
          <p className="mt-1 text-xs text-slate-500">uc101_proy004</p>
        </div>
      </aside>

      <section className="lg:ml-64">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-4 py-4 backdrop-blur lg:px-8">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">PROY-004 · Kardex operativo</p>
              <h2 className="text-2xl font-semibold text-slate-950">Duralon Inventario</h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar producto"
                  className="h-10 w-56 rounded border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-slate-500"
                />
              </div>
              <button
                type="button"
                onClick={refresh}
                className="flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw size={16} />
                Actualizar
              </button>
            </div>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto lg:hidden">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id);
                  setNotice('');
                }}
                className={`whitespace-nowrap rounded px-3 py-2 text-sm font-medium ${
                  activeTab === tab.id ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </header>

        <div className="px-4 py-5 lg:px-8">
          {error && <div className="mb-4 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          {notice && <div className="mb-4 rounded border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</div>}
          <Kpis data={data} loading={loading} />

          {activeTab === 'inventario' && <InventoryTab products={filteredProducts} stock={data.stock} lotStock={data.lot_stock || []} />}
          {activeTab === 'producto' && (
            <ProductTab
              products={filteredProducts}
              stock={data.stock}
              movements={[...data.sales, ...data.purchases, ...data.adjustments]}
              saving={saving}
              setSaving={setSaving}
              refresh={refresh}
              setNotice={setNotice}
            />
          )}
          {activeTab === 'proveedores' && <PartyTab type="supplier" parties={data.suppliers} saving={saving} setSaving={setSaving} refresh={refresh} setNotice={setNotice} />}
          {activeTab === 'clientes' && <PartyTab type="customer" parties={data.customers} saving={saving} setSaving={setSaving} refresh={refresh} setNotice={setNotice} />}
          {activeTab === 'kardex' && <KardexTab products={data.products} />}
          {activeTab === 'ventas' && (
            <RemisionesTab setNotice={setNotice} />
          )}
          {activeTab === 'compras' && (
            <PurchaseTab
              products={data.products}
              suppliers={data.suppliers}
              saving={saving}
              setSaving={setSaving}
              refresh={refresh}
              setNotice={setNotice}
            />
          )}
        </div>
      </section>
    </main>
  );
}

function ProductTab({
  products,
  stock,
  movements,
  saving,
  setSaving,
  refresh,
  setNotice,
}: {
  products: Product[];
  stock: DashboardData['stock'];
  movements: KardexMovement[];
  saving: boolean;
  setSaving: (value: boolean) => void;
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const [selectedProductId, setSelectedProductId] = useState('');
  const selectedProduct = products.find((product) => product.id === selectedProductId) || products[0];
  const productId = selectedProduct?.id || '';
  const productStock = stock.find((row) => row.product_id === productId);
  const productMovements = movements
    .filter((movement) => movement.product_id === productId)
    .sort((a, b) => String(b.movement_date).localeCompare(String(a.movement_date)));
  const categoryOptions = uniqueOptions(products.map((product) => product.category));
  const category2Options = uniqueOptions(products.map((product) => product.category_2));

  useEffect(() => {
    if (!selectedProductId && products[0]?.id) setSelectedProductId(products[0].id);
  }, [products, selectedProductId]);

  async function saveProduct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSaving(true);
    try {
      const form = new FormData(formElement);
      const payload: any = Object.fromEntries(form.entries());
      payload.is_key_product = payload.is_key_product === 'on';
      const res = await fetch('/api/products', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo guardar producto');
      formElement.reset();
      await refresh();
      setNotice(`Producto guardado: ${json.data?.folio || payload.product_name}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo guardar producto');
    } finally {
      setSaving(false);
    }
  }

  async function saveAdjustment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProduct) return;
    const formElement = event.currentTarget;
    setSaving(true);
    try {
      const form = new FormData(formElement);
      const payload: any = Object.fromEntries(form.entries());
      payload.source_type = 'ajuste';
      payload.product_id = selectedProduct.id;
      payload.product_name_snapshot = selectedProduct.product_name;
      const res = await fetch('/api/kardex', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo guardar ajuste');
      formElement.reset();
      await refresh();
      setNotice(`Ajuste guardado: ${json.data?.source_folio || json.data?.folio || selectedProduct.product_name}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo guardar ajuste');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <datalist id="product-category-options">
        {categoryOptions.map((value) => <option key={value} value={value} />)}
      </datalist>
      <datalist id="product-category-2-options">
        {category2Options.map((value) => <option key={value} value={value} />)}
      </datalist>
      <ProductCatalogTable products={products} categoryOptions={categoryOptions} category2Options={category2Options} refresh={refresh} setNotice={setNotice} />
      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
      <div className="space-y-5">
        <form onSubmit={saveProduct} className="rounded border border-slate-200 bg-white p-4">
          <SectionTitle title="Agregar producto" subtitle="Alta de catalogo" compact />
          <Field name="product_name" label="Nombre" required />
          <Field name="product_key" label="Clave interna" />
          <Field name="sku" label="SKU" />
          <Field name="category" label="Categoria" list="product-category-options" />
          <Field name="category_2" label="Categoria 2" list="product-category-2-options" />
          <Field name="brand" label="Marca" />
          <div className="grid grid-cols-2 gap-3">
            <Field name="unit" label="Unidad" defaultValue="pieza" required />
            <Field name="min_stock" label="Minimo" type="number" step="0.01" />
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
            <input name="is_key_product" type="checkbox" className="h-4 w-4 rounded border-slate-300" />
            Producto clave
          </label>
          <button className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 text-sm font-semibold text-white hover:bg-slate-800" disabled={saving}>
            <PackagePlus size={16} />
            Guardar producto
          </button>
        </form>

        <form onSubmit={saveAdjustment} className="rounded border border-slate-200 bg-white p-4">
          <SectionTitle title="Ajuste manual" subtitle="Entrada o salida sin compra/remision" compact />
          <Select
            name="adjustment_direction"
            label="Tipo de ajuste"
            options={[
              { value: 'entrada', label: 'Entrada manual' },
              { value: 'salida', label: 'Salida manual' },
            ]}
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Field name="movement_date" label="Fecha" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} />
            <Field name="quantity" label="Cantidad" type="number" step="0.01" required />
          </div>
          <TextArea name="notes" label="Motivo" />
          <button className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 text-sm font-semibold text-white hover:bg-slate-800" disabled={saving || !selectedProduct}>
            <Save size={16} />
            Guardar ajuste
          </button>
        </form>
      </div>

      <section className="rounded border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Kardex por producto</h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Stock: {qty(productStock?.quantity)} · Entradas: {qty(productStock?.total_in)} · Salidas: {qty(productStock?.total_out)}
              </p>
            </div>
            <select
              value={productId}
              onChange={(event) => setSelectedProductId(event.target.value)}
              className="h-10 rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500"
            >
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.product_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <ProductKardexTable movements={productMovements} />
      </section>
      </div>
    </div>
  );
}

function ProductCatalogTable({
  products,
  categoryOptions,
  category2Options,
  refresh,
  setNotice,
}: {
  products: Product[];
  categoryOptions: string[];
  category2Options: string[];
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const sorted = [...products].sort((a, b) => Number(b.is_key_product) - Number(a.is_key_product) || String(a.product_name || '').localeCompare(String(b.product_name || ''))).slice(0, 20);
  return (
    <section className="rounded border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Catalogo de productos</h3>
          <p className="mt-0.5 text-xs text-slate-500">Maximo 20 visibles, productos clave primero</p>
        </div>
        <button type="button" className="inline-flex h-9 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <Search size={15} />
          Buscar producto
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[1360px] text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3 text-left">Clave</th>
              <th className="px-3 py-3 text-left">Nombre</th>
              <th className="px-3 py-3 text-left">Folio</th>
              <th className="px-3 py-3 text-left">SKU</th>
              <th className="px-3 py-3 text-left">Categoria</th>
              <th className="px-3 py-3 text-left">Categoria 2</th>
              <th className="px-3 py-3 text-left">Marca</th>
              <th className="px-3 py-3 text-left">Unidad</th>
              <th className="px-3 py-3 text-right">Minimo</th>
              <th className="px-3 py-3 text-left">Clave</th>
              <th className="px-3 py-3 text-left">Activo</th>
              <th className="px-3 py-3 text-right">Accion</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((product) => <ProductCatalogRow key={product.id} product={product} categoryOptions={categoryOptions} category2Options={category2Options} refresh={refresh} setNotice={setNotice} />)}
            {sorted.length === 0 && <tr><td colSpan={12} className="px-4 py-8 text-center text-sm text-slate-500">Sin productos</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProductCatalogRow({
  product,
  categoryOptions,
  category2Options,
  refresh,
  setNotice,
}: {
  product: Product;
  categoryOptions: string[];
  category2Options: string[];
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({
    product_key: product.product_key || '',
    product_name: product.product_name || '',
    sku: product.sku || '',
    category: product.category || '',
    category_2: product.category_2 || '',
    brand: product.brand || '',
    unit: product.unit || 'pieza',
    min_stock: Number(product.min_stock || 0),
    is_key_product: product.is_key_product || false,
    active: product.active !== false,
  });
  const inputClass = 'h-9 w-full rounded border border-slate-200 px-2 text-sm outline-none focus:border-slate-500';

  async function save() {
    if (!draft.product_name.trim()) {
      window.alert('Nombre es obligatorio');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('/api/products', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: product.id, ...draft }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo actualizar producto');
      await refresh();
      setEditing(false);
      setNotice(`Producto actualizado: ${draft.product_name}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo actualizar producto');
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className="border-b border-slate-100">
      <td className="px-3 py-2">{editing ? <input className={inputClass} value={draft.product_key} onChange={(event) => setDraft((current) => ({ ...current, product_key: event.target.value }))} /> : <span className="text-slate-600">{draft.product_key || '-'}</span>}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} value={draft.product_name} onChange={(event) => setDraft((current) => ({ ...current, product_name: event.target.value }))} /> : <span className="font-medium text-slate-900">{draft.product_name}</span>}</td>
      <td className="px-3 py-3 text-slate-500">{product.folio}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} value={draft.sku} onChange={(event) => setDraft((current) => ({ ...current, sku: event.target.value }))} /> : <span className="text-slate-600">{draft.sku || '-'}</span>}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} list="product-category-options" value={draft.category} onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))} /> : <span className="text-slate-600">{draft.category || '-'}</span>}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} list="product-category-2-options" value={draft.category_2} onChange={(event) => setDraft((current) => ({ ...current, category_2: event.target.value }))} /> : <span className="text-slate-600">{draft.category_2 || '-'}</span>}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} value={draft.brand} onChange={(event) => setDraft((current) => ({ ...current, brand: event.target.value }))} /> : <span className="text-slate-600">{draft.brand || '-'}</span>}</td>
      <td className="px-3 py-2">{editing ? <input className={inputClass} value={draft.unit} onChange={(event) => setDraft((current) => ({ ...current, unit: event.target.value }))} /> : <span className="text-slate-600">{draft.unit}</span>}</td>
      <td className="px-3 py-2">{editing ? <input type="number" step="0.01" className={`${inputClass} text-right`} value={draft.min_stock} onChange={(event) => setDraft((current) => ({ ...current, min_stock: Number(event.target.value) }))} /> : <span className="block text-right text-slate-600">{qty(draft.min_stock)}</span>}</td>
      <td className="px-3 py-3"><input type="checkbox" checked={draft.is_key_product} disabled={!editing} onChange={(event) => setDraft((current) => ({ ...current, is_key_product: event.target.checked }))} /></td>
      <td className="px-3 py-3"><input type="checkbox" checked={draft.active} disabled={!editing} onChange={(event) => setDraft((current) => ({ ...current, active: event.target.checked }))} /></td>
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1">
          <button type="button" onClick={() => setEditing(true)} title="Editar" className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 text-slate-700 hover:bg-slate-50"><Pencil size={15} /></button>
          <button type="button" onClick={save} disabled={saving} title="Guardar" className="inline-flex h-8 w-8 items-center justify-center rounded bg-slate-900 text-white hover:bg-slate-800"><Save size={15} /></button>
        </div>
      </td>
    </tr>
  );
}

function Kpis({ data, loading }: { data: DashboardData; loading: boolean }) {
  const cards = [
    { label: 'Productos', value: data.products.length, sub: 'catalogo activo', icon: Boxes },
    { label: 'Clientes', value: data.customers.length, sub: 'compradores', icon: Store },
    { label: 'Proveedores', value: data.suppliers.length, sub: 'abastecimiento', icon: Truck },
    { label: 'CXC ventas', value: money(data.receivables_total), sub: 'saldo pendiente', icon: CircleDollarSign },
    { label: 'CXP compras', value: money(data.payables_total), sub: 'saldo pendiente', icon: CircleDollarSign },
  ];
  return (
    <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.label} className="rounded border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase text-slate-500">{card.label}</p>
              <Icon size={17} className="text-slate-400" />
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-950">{loading ? '...' : card.value}</p>
            <p className="mt-1 text-xs text-slate-500">{card.sub}</p>
          </div>
        );
      })}
    </div>
  );
}

function OldInventoryTab({ products, stock, movements }: { products: Product[]; stock: DashboardData['stock']; movements: KardexMovement[] }) {
  const stockByProduct = new Map(stock.map((row) => [row.product_id, row]));
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <section className="rounded border border-slate-200 bg-white">
        <SectionTitle title="Inventario actual" subtitle="Existencias calculadas desde kardex" />
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left">Producto</th>
                <th className="px-4 py-3 text-left">Folio</th>
                <th className="px-4 py-3 text-right">Entrada</th>
                <th className="px-4 py-3 text-right">Salida</th>
                <th className="px-4 py-3 text-right">Stock</th>
                <th className="px-4 py-3 text-left">Unidad</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => {
                const row = stockByProduct.get(product.id);
                return (
                  <tr key={product.id} className="border-b border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">{product.product_name}</td>
                    <td className="px-4 py-3 text-slate-500">{product.folio}</td>
                    <td className="px-4 py-3 text-right">{qty(row?.total_in)}</td>
                    <td className="px-4 py-3 text-right">{qty(row?.total_out)}</td>
                    <td className={`px-4 py-3 text-right font-semibold ${Number(row?.quantity || 0) < 0 ? 'text-red-600' : 'text-slate-950'}`}>{qty(row?.quantity)}</td>
                    <td className="px-4 py-3 text-slate-500">{product.unit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      <section className="rounded border border-slate-200 bg-white">
        <SectionTitle title="Ultimos movimientos" subtitle="Compras y remisiones recientes" />
        <div className="divide-y divide-slate-100">
          {movements.slice(0, 10).map((movement) => (
            <div key={movement.id} className="px-4 py-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-slate-900">{movement.product_name_snapshot || 'Producto'}</p>
                <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{movement.source_folio}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {movement.source_type} · {movement.movement_date} · {qty(movement.quantity_in || movement.quantity_out)}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function InventoryTab({ products, stock, lotStock }: { products: Product[]; stock: DashboardData['stock']; lotStock: NonNullable<DashboardData['lot_stock']> }) {
  const [showKeyOnly, setShowKeyOnly] = useState(true);
  const visibleIds = new Set(products.map((product) => product.id));
  const visibleStock = stock.filter((row) => visibleIds.has(row.product_id));
  const visibleLotStock = lotStock.filter((row) => visibleIds.has(row.product_id));
  const filteredStock = showKeyOnly ? visibleStock.filter((row) => row.is_key_product) : visibleStock;
  const filteredLotStock = showKeyOnly ? visibleLotStock.filter((row) => row.is_key_product) : visibleLotStock;
  const filterLabel = showKeyOnly ? 'productos clave' : 'todos los productos';
  return (
    <div className="space-y-5">
      <section className="rounded border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Inventario por lote</h3>
            <p className="mt-0.5 text-xs text-slate-500">{`${filteredLotStock.length} lotes visibles - ${filterLabel}`}</p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={showKeyOnly}
              onChange={(event) => setShowKeyOnly(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Solo productos clave
          </label>
        </div>
        <InventoryLotTable rows={filteredLotStock} />
      </section>
      <section className="rounded border border-slate-200 bg-white">
        <SectionTitle title="Inventario actual" subtitle={`${filteredStock.length} ${filterLabel}`} />
        <InventoryStockTable rows={filteredStock} compact={!showKeyOnly} />
      </section>
    </div>
  );
}

function InventoryLotTable({ rows }: { rows: NonNullable<DashboardData['lot_stock']> }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[1320px] text-xs">
        <thead className="border-y border-slate-200 bg-slate-50 uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left">Producto / lote</th>
            <th className="px-4 py-3 text-left">Lote</th>
            <th className="px-4 py-3 text-left">Marca</th>
            <th className="px-4 py-3 text-left">Categoria</th>
            <th className="px-4 py-3 text-left">Categoria 2</th>
            <th className="px-4 py-3 text-right">Stock</th>
            <th className="px-4 py-3 text-right">Entrada</th>
            <th className="px-4 py-3 text-right">Salida</th>
            <th className="px-4 py-3 text-left">Unidad</th>
            <th className="px-4 py-3 text-right">Costo lote</th>
            <th className="px-4 py-3 text-right">Ultimo costo</th>
            <th className="px-4 py-3 text-right">Valor est.</th>
            <th className="px-4 py-3 text-left">Ult. mov.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.product_id}-${row.lot_code}`} className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{row.display_name}</td>
              <td className="px-4 py-3 text-slate-600">{row.lot_code}</td>
              <td className="px-4 py-3 text-slate-600">{row.brand || '-'}</td>
              <td className="px-4 py-3 text-slate-600">{row.category || '-'}</td>
              <td className="px-4 py-3 text-slate-600">{row.category_2 || '-'}</td>
              <td className={`px-4 py-3 text-right font-semibold ${Number(row.quantity || 0) < 0 ? 'text-red-600' : 'text-slate-950'}`}>{qty(row.quantity)}</td>
              <td className="px-4 py-3 text-right">{qty(row.total_in)}</td>
              <td className="px-4 py-3 text-right">{qty(row.total_out)}</td>
              <td className="px-4 py-3 text-slate-500">{row.unit}</td>
              <td className="px-4 py-3 text-right">{money(row.avg_cost)}</td>
              <td className="px-4 py-3 text-right">{money(row.last_cost)}</td>
              <td className="px-4 py-3 text-right">{money(row.estimated_value)}</td>
              <td className="px-4 py-3 text-slate-500">{row.last_movement_date || '-'}</td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={13} className="px-4 py-8 text-center text-sm text-slate-500">Sin lotes para mostrar</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function InventoryStockTable({ rows, compact }: { rows: DashboardData['stock']; compact?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className={`${compact ? 'min-w-[1180px] text-xs' : 'min-w-[1180px] text-sm'}`}>
        <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left">Semaforo</th>
            <th className="px-4 py-3 text-left">Producto</th>
            <th className="px-4 py-3 text-left">Folio</th>
            <th className="px-4 py-3 text-left">Categoria</th>
            <th className="px-4 py-3 text-right">Stock</th>
            <th className="px-4 py-3 text-right">Minimo</th>
            <th className="px-4 py-3 text-right">Diferencia</th>
            <th className="px-4 py-3 text-right">Entrada</th>
            <th className="px-4 py-3 text-right">Salida</th>
            <th className="px-4 py-3 text-left">Unidad</th>
            <th className="px-4 py-3 text-right">Costo prom.</th>
            <th className="px-4 py-3 text-right">Ultimo costo</th>
            <th className="px-4 py-3 text-right">Valor est.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.product_id} className="border-b border-slate-100">
              <td className="px-4 py-3"><StockBadge status={row.stock_status} /></td>
              <td className="px-4 py-3 font-medium text-slate-900">{row.product_name}</td>
              <td className="px-4 py-3 text-slate-500">{row.folio}</td>
              <td className="px-4 py-3 text-slate-600">{row.category || '-'}</td>
              <td className={`px-4 py-3 text-right font-semibold ${Number(row.quantity || 0) < 0 ? 'text-red-600' : 'text-slate-950'}`}>{qty(row.quantity)}</td>
              <td className="px-4 py-3 text-right">{qty(row.min_stock)}</td>
              <td className="px-4 py-3 text-right">{qty(row.stock_delta)}</td>
              <td className="px-4 py-3 text-right">{qty(row.total_in)}</td>
              <td className="px-4 py-3 text-right">{qty(row.total_out)}</td>
              <td className="px-4 py-3 text-slate-500">{row.unit}</td>
              <td className="px-4 py-3 text-right">{money(row.avg_cost)}</td>
              <td className="px-4 py-3 text-right">{money(row.last_cost)}</td>
              <td className="px-4 py-3 text-right">{money(row.estimated_value)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={13} className="px-4 py-8 text-center text-sm text-slate-500">Sin productos para mostrar</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function StockBadge({ status }: { status?: string }) {
  const style = status === 'negativo' ? 'bg-red-100 text-red-700' : status === 'bajo' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700';
  const label = status === 'negativo' ? 'Negativo' : status === 'bajo' ? 'Bajo' : 'OK';
  return <span className={`inline-flex rounded px-2 py-1 text-xs font-semibold ${style}`}>{label}</span>;
}

function PartyTab({
  type,
  parties,
  saving,
  setSaving,
  refresh,
  setNotice,
}: {
  type: 'customer' | 'supplier';
  parties: Party[];
  saving: boolean;
  setSaving: (value: boolean) => void;
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const label = type === 'customer' ? 'Cliente' : 'Proveedor';
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSaving(true);
    try {
      const form = new FormData(formElement);
      const payload = Object.fromEntries(form.entries());
      payload.party_type = type;
      const res = await fetch('/api/parties', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || `No se pudo guardar ${label.toLowerCase()}`);
      formElement.reset();
      await refresh();
      setNotice(`${label} guardado: ${json.data?.folio || payload.party_name}`);
    } catch (err: any) {
      window.alert(err.message || `No se pudo guardar ${label.toLowerCase()}`);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
      <form onSubmit={save} className="rounded border border-slate-200 bg-white p-4">
        <SectionTitle title={`Agregar ${label.toLowerCase()}`} subtitle="Alta rapida para operacion" compact />
        <Field name="party_name" label="Nombre" required />
        <Field name="legal_name" label="Razon social" />
        <Field name="rfc" label="RFC" />
        <Field name="phone" label="Telefono" />
        <Field name="email" label="Email" type="email" />
        <Field name="address" label="Direccion" />
        <button className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 text-sm font-semibold text-white hover:bg-slate-800" disabled={saving}>
          <UserRoundPlus size={16} />
          Guardar {label.toLowerCase()}
        </button>
      </form>
      <PartyTable parties={parties} refresh={refresh} setNotice={setNotice} />
    </div>
  );
}

function PurchaseTab({
  products,
  suppliers,
  saving,
  setSaving,
  refresh,
  setNotice,
}: {
  products: Product[];
  suppliers: Party[];
  saving: boolean;
  setSaving: (value: boolean) => void;
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [supplierId, setSupplierId] = useState('');
  const [movementDate, setMovementDate] = useState(today);
  const [externalFolio, setExternalFolio] = useState('');
  const [paidAmount, setPaidAmount] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<PurchaseLine[]>([newPurchaseLine()]);
  const [purchases, setPurchases] = useState<PurchaseSummary[]>([]);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(today);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPurchases();
  }, []);

  function updateItem(id: string, key: keyof PurchaseLine, value: string) {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, [key]: value } : item)));
  }

  function addItem() {
    setItems((current) => [...current, newPurchaseLine()]);
  }

  function removeItem(id: string) {
    setItems((current) => (current.length === 1 ? current : current.filter((item) => item.id !== id)));
  }

  const total = items.reduce((sum, item) => sum + purchaseLineTotal(item), 0);
  const balance = Math.max(total - Number(paidAmount || 0), 0);

  async function savePurchase(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanItems = items
      .map((item) => ({
        product_id: item.product_id,
        lot_code: item.lot_code,
        quantity: Number(item.quantity || 0),
        unit_cost: Number(item.unit_cost || 0),
        tax_rate: Number(item.tax_rate || 0),
        notes: item.notes,
      }))
      .filter((item) => item.product_id && item.quantity > 0);
    if (!supplierId) {
      window.alert('Proveedor es obligatorio');
      return;
    }
    if (!cleanItems.length) {
      window.alert('Agrega al menos un renglon valido');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('/api/purchases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier_id: supplierId,
          movement_date: movementDate,
          external_folio: externalFolio,
          paid_amount: Number(paidAmount || 0),
          notes,
          items: cleanItems,
        }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo guardar compra');
      setSupplierId('');
      setMovementDate(today);
      setExternalFolio('');
      setPaidAmount('');
      setNotes('');
      setItems([newPurchaseLine()]);
      await refresh();
      await loadPurchases();
      setNotice(`Compra guardada: ${json.data?.source_folio || ''}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo guardar compra');
    } finally {
      setSaving(false);
    }
  }

  async function loadPurchases() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate, limit: '20', t: String(Date.now()) });
      const res = await fetch(`/api/purchases?${params.toString()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudieron cargar compras');
      setPurchases(json.data || []);
    } catch (err: any) {
      window.alert(err.message || 'No se pudieron cargar compras');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={savePurchase} className="rounded border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-950">Agregar compra / entrada</h3>
          <p className="mt-0.5 text-xs text-slate-500">Compra multi-renglon con entrada automatica al kardex</p>
        </div>
        <div className="grid gap-4 p-4 lg:grid-cols-4">
          <label className="block lg:col-span-2">
            <span className="text-xs font-medium text-slate-600">Proveedor</span>
            <select value={supplierId} onChange={(event) => setSupplierId(event.target.value)} required className="mt-1 h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
              <option value="">Seleccionar</option>
              {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.party_name}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Fecha</span>
            <input type="date" value={movementDate} onChange={(event) => setMovementDate(event.target.value)} required className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Folio proveedor</span>
            <input value={externalFolio} onChange={(event) => setExternalFolio(event.target.value)} className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
          </label>
        </div>

        <div className="overflow-x-auto px-4">
          <table className="min-w-[1240px] text-sm">
            <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-3 text-left">Producto</th>
                <th className="px-3 py-3 text-left">Lote</th>
                <th className="px-3 py-3 text-right">Cantidad</th>
                <th className="px-3 py-3 text-right">Costo unitario</th>
                <th className="px-3 py-3 text-right">IVA</th>
                <th className="px-3 py-3 text-right">Subtotal</th>
                <th className="px-3 py-3 text-right">Total</th>
                <th className="px-3 py-3 text-left">Notas</th>
                <th className="px-3 py-3 text-right">Accion</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const lineSubtotal = purchaseLineSubtotal(item);
                const lineTotal = purchaseLineTotal(item);
                return (
                  <tr key={item.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">
                      <select value={item.product_id} onChange={(event) => updateItem(item.id, 'product_id', event.target.value)} required className="h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
                        <option value="">Seleccionar</option>
                        {products.map((product) => <option key={product.id} value={product.id}>{product.product_name} · {product.unit}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.lot_code} onChange={(event) => updateItem(item.id, 'lot_code', event.target.value)} placeholder="GENERAL" className="h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
                    </td>
                    <td className="px-3 py-2">
                      <input type="number" step="0.01" value={item.quantity} onChange={(event) => updateItem(item.id, 'quantity', event.target.value)} required className="h-10 w-full rounded border border-slate-200 px-3 text-right text-sm outline-none focus:border-slate-500" />
                    </td>
                    <td className="px-3 py-2">
                      <input type="number" step="0.01" value={item.unit_cost} onChange={(event) => updateItem(item.id, 'unit_cost', event.target.value)} className="h-10 w-full rounded border border-slate-200 px-3 text-right text-sm outline-none focus:border-slate-500" />
                    </td>
                    <td className="px-3 py-2">
                      <select value={item.tax_rate} onChange={(event) => updateItem(item.id, 'tax_rate', event.target.value)} className="h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
                        <option value="0">0%</option>
                        <option value="0.08">8%</option>
                        <option value="0.16">16%</option>
                      </select>
                    </td>
                    <td className="px-3 py-2 text-right text-slate-700">{money(lineSubtotal)}</td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-900">{money(lineTotal)}</td>
                    <td className="px-3 py-2">
                      <input value={item.notes} onChange={(event) => updateItem(item.id, 'notes', event.target.value)} className="h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" onClick={() => removeItem(item.id)} disabled={items.length === 1} className="inline-flex h-9 items-center justify-center rounded border border-red-200 bg-white px-3 text-red-700 hover:bg-red-50 disabled:opacity-40">
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="grid gap-4 p-4 lg:grid-cols-[1fr_220px_220px_220px]">
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Notas generales</span>
            <input value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Pagado</span>
            <input type="number" step="0.01" value={paidAmount} onChange={(event) => setPaidAmount(event.target.value)} className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-right text-sm outline-none focus:border-slate-500" />
          </label>
          <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs font-medium text-slate-500">Total</p>
            <p className="text-lg font-semibold text-slate-950">{money(total)}</p>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-xs font-medium text-slate-500">Saldo</p>
            <p className="text-lg font-semibold text-slate-950">{money(balance)}</p>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
          <button type="button" onClick={addItem} className="inline-flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <PackagePlus size={16} />
            Agregar renglon
          </button>
          <button type="submit" disabled={saving} className="inline-flex h-10 items-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60">
            <Save size={16} />
            Guardar compra
          </button>
        </div>
      </form>

      <section className="rounded border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Ultimas compras</h3>
            <p className="mt-0.5 text-xs text-slate-500">{loading ? 'Cargando...' : `${purchases.length} documentos`}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
            <button type="button" onClick={loadPurchases} disabled={loading} className="inline-flex h-10 items-center gap-2 rounded bg-slate-900 px-3 text-sm font-semibold text-white hover:bg-slate-800">
              <RefreshCw size={15} />
              Ver
            </button>
          </div>
        </div>
        <PurchaseTable purchases={purchases} />
      </section>
    </div>
  );
}

function newPurchaseLine(): PurchaseLine {
  return { id: `${Date.now()}-${Math.random().toString(16).slice(2)}`, product_id: '', lot_code: '', quantity: '', unit_cost: '', tax_rate: '0.16', notes: '' };
}

function uniqueOptions(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((value) => String(value || '').trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

function purchaseLineSubtotal(item: PurchaseLine) {
  return Number(item.quantity || 0) * Number(item.unit_cost || 0);
}

function purchaseLineTotal(item: PurchaseLine) {
  const subtotal = purchaseLineSubtotal(item);
  return subtotal + subtotal * Number(item.tax_rate || 0);
}

function purchaseTaxAmount(purchase: PurchaseSummary) {
  return (purchase.items || []).reduce((sum, item) => sum + movementTaxAmount(item), 0);
}

function purchaseNetAmount(purchase: PurchaseSummary) {
  const net = (purchase.items || []).reduce((sum, item) => sum + movementNetAmount(item), 0);
  return net || Math.max(Number(purchase.total_cost || 0) - purchaseTaxAmount(purchase), 0);
}

function PurchaseTable({ purchases }: { purchases: PurchaseSummary[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[1080px] text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left">Folio</th>
            <th className="px-4 py-3 text-left">Fecha</th>
            <th className="px-4 py-3 text-left">Proveedor</th>
            <th className="px-4 py-3 text-left">Folio prov.</th>
            <th className="px-4 py-3 text-right">Renglones</th>
            <th className="px-4 py-3 text-right">Neto</th>
            <th className="px-4 py-3 text-right">IVA</th>
            <th className="px-4 py-3 text-right">Total</th>
            <th className="px-4 py-3 text-right">Pagado</th>
            <th className="px-4 py-3 text-right">Saldo</th>
            <th className="px-4 py-3 text-left">Estatus</th>
          </tr>
        </thead>
        <tbody>
          {purchases.map((purchase) => (
            <tr key={purchase.source_folio} className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{purchase.source_folio}</td>
              <td className="px-4 py-3 text-slate-500">{purchase.movement_date}</td>
              <td className="px-4 py-3 text-slate-700">{purchase.supplier_name_snapshot}</td>
              <td className="px-4 py-3 text-slate-500">{purchase.external_folio || '-'}</td>
              <td className="px-4 py-3 text-right">{purchase.line_count}</td>
              <td className="px-4 py-3 text-right">{money(purchaseNetAmount(purchase))}</td>
              <td className="px-4 py-3 text-right">{money(purchaseTaxAmount(purchase))}</td>
              <td className="px-4 py-3 text-right">{money(purchase.total_cost)}</td>
              <td className="px-4 py-3 text-right">{money(purchase.paid_amount)}</td>
              <td className="px-4 py-3 text-right">{money(purchase.balance_amount)}</td>
              <td className="px-4 py-3 text-slate-500">{purchase.payment_status}</td>
            </tr>
          ))}
          {purchases.length === 0 && <tr><td colSpan={11} className="px-4 py-8 text-center text-sm text-slate-500">Sin compras para mostrar</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function MovementTab({
  type,
  products,
  parties,
  movements,
  saving,
  setSaving,
  refresh,
  setNotice,
}: {
  type: 'compra' | 'remision';
  products: Product[];
  parties: Party[];
  movements: KardexMovement[];
  saving: boolean;
  setSaving: (value: boolean) => void;
  refresh: RefreshFn;
  setNotice: (value: string) => void;
}) {
  const isSale = type === 'remision';
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSaving(true);
    try {
      const form = new FormData(formElement);
      const payload: any = Object.fromEntries(form.entries());
      const product = products.find((row) => row.id === payload.product_id);
      const party = parties.find((row) => row.id === payload.party_id);
      payload.source_type = type;
      payload.product_name_snapshot = product?.product_name || '';
      payload.party_name_snapshot = party?.party_name || '';
      const res = await fetch('/api/kardex', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo guardar movimiento');
      formElement.reset();
      await refresh();
      setNotice(`${isSale ? 'Venta' : 'Compra'} guardada: ${json.data?.source_folio || json.data?.folio || ''}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo guardar movimiento');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <form onSubmit={save} className="rounded border border-slate-200 bg-white p-4">
        <SectionTitle title={isSale ? 'Agregar venta / salida' : 'Agregar compra / entrada'} subtitle={isSale ? 'Remision de venta' : 'Entrada por compra'} compact />
        <Select name="party_id" label={isSale ? 'Cliente' : 'Proveedor'} options={parties.map((p) => ({ value: p.id, label: p.party_name }))} required />
        <Select name="product_id" label="Producto" options={products.map((p) => ({ value: p.id, label: `${p.product_name} · ${p.unit}` }))} required />
        <div className="grid grid-cols-2 gap-3">
          <Field name="movement_date" label="Fecha" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} />
          <Field name="quantity" label="Cantidad" type="number" step="0.01" required />
        </div>
        {isSale ? <Field name="unit_price" label="Precio unitario" type="number" step="0.01" /> : <Field name="unit_cost" label="Costo unitario" type="number" step="0.01" />}
        <Field name="paid_amount" label={isSale ? 'Cobrado' : 'Pagado'} type="number" step="0.01" />
        <Field name="external_folio" label="Folio externo" />
        <TextArea name="notes" label="Notas" />
        <button className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 text-sm font-semibold text-white hover:bg-slate-800" disabled={saving}>
          <Save size={16} />
          Guardar movimiento
        </button>
      </form>
      <MovementTable movements={movements} isSale={isSale} />
    </div>
  );
}

function PartyTable({ parties, refresh, setNotice }: { parties: Party[]; refresh: RefreshFn; setNotice: (value: string) => void }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <SectionTitle title="Registros" subtitle={`${parties.length} activos`} />
      <div className="overflow-x-auto">
        <table className="min-w-[980px] text-sm">
          <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Folio</th>
              <th className="px-4 py-3 text-left">Razon social</th>
              <th className="px-4 py-3 text-left">RFC</th>
              <th className="px-4 py-3 text-left">Telefono</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Direccion</th>
              <th className="px-4 py-3 text-left">Activo</th>
              <th className="px-4 py-3 text-right">Accion</th>
            </tr>
          </thead>
          <tbody>
            {parties.map((party) => (
              <PartyRow key={party.id} party={party} refresh={refresh} setNotice={setNotice} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PartyRow({ party, refresh, setNotice }: { party: Party; refresh: RefreshFn; setNotice: (value: string) => void }) {
  const [draft, setDraft] = useState({
    party_name: party.party_name || '',
    legal_name: party.legal_name || '',
    rfc: party.rfc || '',
    phone: party.phone || '',
    email: party.email || '',
    address: party.address || '',
    active: party.active !== false,
  });
  const [saving, setSaving] = useState(false);

  function update(key: keyof typeof draft, value: string | boolean) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    if (!draft.party_name.trim()) {
      window.alert('Nombre es obligatorio');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('/api/parties', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: party.id, party_type: party.party_type, ...draft }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo actualizar registro');
      await refresh();
      setNotice(`Registro actualizado: ${json.data?.folio || draft.party_name}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo actualizar registro');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Borrar ${party.party_name}?`)) return;
    setSaving(true);
    try {
      const res = await fetch('/api/parties', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: party.id, party_type: party.party_type }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo borrar registro');
      await refresh();
      setNotice(`Registro borrado: ${party.party_name}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo borrar registro');
    } finally {
      setSaving(false);
    }
  }

  const inputClass = 'h-9 w-full rounded border border-slate-200 px-2 text-sm outline-none focus:border-slate-500';

  return (
    <tr className="border-b border-slate-100 align-top">
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.party_name} onChange={(event) => update('party_name', event.target.value)} />
      </td>
      <td className="px-3 py-3 text-slate-500">{party.folio}</td>
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.legal_name} onChange={(event) => update('legal_name', event.target.value)} />
      </td>
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.rfc} onChange={(event) => update('rfc', event.target.value)} />
      </td>
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.phone} onChange={(event) => update('phone', event.target.value)} />
      </td>
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.email} onChange={(event) => update('email', event.target.value)} />
      </td>
      <td className="px-3 py-2">
        <input className={inputClass} value={draft.address} onChange={(event) => update('address', event.target.value)} />
      </td>
      <td className="px-3 py-3">
        <input type="checkbox" checked={draft.active} onChange={(event) => update('active', event.target.checked)} />
      </td>
      <td className="px-3 py-2 text-right">
        <button
          type="button"
          onClick={remove}
          disabled={saving}
          className="mr-2 inline-flex h-9 items-center gap-2 rounded border border-red-200 bg-white px-3 text-sm font-semibold text-red-700 hover:bg-red-50"
        >
          <Trash2 size={15} />
          Borrar
        </button>
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded bg-slate-900 px-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          <Save size={15} />
          Guardar
        </button>
      </td>
    </tr>
  );
}

function RemisionesTab({ setNotice }: { setNotice: (value: string) => void }) {
  const [remisiones, setRemisiones] = useState<RemisionDoc[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [detail, setDetail] = useState<RemisionDetail | null>(null);
  const [matrix, setMatrix] = useState<MatrixData | null>(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`/api/remisiones?limit=100&t=${Date.now()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudieron cargar remisiones');
      const rows = json.data || [];
      setRemisiones(rows);
      if (!selectedId && rows[0]?.id) setSelectedId(rows[0].id);
    } catch (err: any) {
      window.alert(err.message || 'No se pudieron cargar remisiones');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (selectedId) loadDetail(selectedId);
  }, [selectedId]);

  useEffect(() => {
    loadMatrix();
  }, []);

  async function loadDetail(id = selectedId) {
    if (!id) return;
    try {
      const res = await fetch(`/api/remisiones?action=detail&id=${encodeURIComponent(id)}&t=${Date.now()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo cargar detalle');
      setDetail(json.data);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo cargar detalle');
    }
  }

  async function loadMatrix() {
    try {
      const params = new URLSearchParams({ action: 'matrix', start_date: startDate, end_date: endDate, t: String(Date.now()) });
      const res = await fetch(`/api/remisiones?${params.toString()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo cargar reporte');
      setMatrix(json.data);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo cargar reporte');
    }
  }

  function printRemision(remision: RemisionDoc) {
    window.open(`/api/remisiones/pdf?id=${encodeURIComponent(remision.id)}`, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="space-y-5">
    <section className="rounded border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Remisiones</h3>
          <p className="mt-0.5 text-xs text-slate-500">{loading ? 'Cargando...' : `${remisiones.length} documentos desde PROY-002`}</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="flex h-9 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={15} />
          Actualizar
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[1120px] text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Remision</th>
              <th className="px-4 py-3 text-left">Fecha</th>
              <th className="px-4 py-3 text-left">Cliente</th>
              <th className="px-4 py-3 text-left">Dir de entrega</th>
              <th className="px-4 py-3 text-left">Estado</th>
              <th className="px-4 py-3 text-left">Folio externo</th>
              <th className="px-4 py-3 text-left">Notas</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-right">Accion</th>
            </tr>
          </thead>
          <tbody>
            {remisiones.map((remision) => (
              <RemisionRow key={remision.id} remision={remision} reload={load} setNotice={setNotice} onPrint={() => printRemision(remision)} onSelect={() => setSelectedId(remision.id)} />
            ))}
            {!loading && remisiones.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-500">
                  Sin remisiones registradas
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
    <RemisionDetailEditor
      detail={detail}
      remisiones={remisiones}
      selectedId={selectedId}
      setSelectedId={setSelectedId}
      reload={async () => {
        await load();
        await loadDetail(selectedId);
        await loadMatrix();
      }}
      setNotice={setNotice}
      onPrint={() => detail && printRemision(detail.remision)}
    />
    <KeyProductMatrixPanel
      matrix={matrix}
      startDate={startDate}
      endDate={endDate}
      setStartDate={setStartDate}
      setEndDate={setEndDate}
      loadMatrix={loadMatrix}
    />
    </div>
  );
}

function RemisionRow({ remision, reload, setNotice, onPrint, onSelect }: { remision: RemisionDoc; reload: () => Promise<void>; setNotice: (value: string) => void; onPrint: () => void; onSelect: () => void }) {
  const [draft, setDraft] = useState({
    status: remision.status || 'emitida',
    delivery_address: remision.delivery_address || '',
    external_folio: remision.external_folio || '',
    notes: remision.notes || '',
  });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputClass = 'h-9 w-full rounded border border-slate-200 px-2 text-sm outline-none focus:border-slate-500';

  async function save() {
    setSaving(true);
    try {
      const res = await fetch('/api/remisiones', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: remision.id, ...draft }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo actualizar remision');
      await reload();
      setEditing(false);
      setNotice(`Remision actualizada: ${remision.folio}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo actualizar remision');
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className="border-b border-slate-100 align-top">
      <td className="px-4 py-3 font-medium text-slate-900"><button type="button" onClick={onSelect} className="text-left font-semibold text-slate-900 hover:underline">{remision.folio}</button></td>
      <td className="px-4 py-3 text-slate-500">{remision.document_date}</td>
      <td className="px-4 py-3 text-slate-700">{remision.customer_name_snapshot}</td>
      <td className="px-3 py-2">
        {editing ? <input className={inputClass} value={draft.delivery_address} onChange={(event) => setDraft((current) => ({ ...current, delivery_address: event.target.value }))} /> : <span className="block py-2 text-slate-600">{draft.delivery_address || '-'}</span>}
      </td>
      <td className="px-3 py-2">
        {editing ? <select className={inputClass} value={draft.status} onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value }))}>
          <option value="emitida">Emitida</option>
          <option value="pendiente">Pendiente</option>
          <option value="pagada">Pagada</option>
          <option value="cancelada">Cancelada</option>
        </select> : <span className="block py-2 text-slate-600">{draft.status}</span>}
      </td>
      <td className="px-3 py-2">
        {editing ? <input className={inputClass} value={draft.external_folio} onChange={(event) => setDraft((current) => ({ ...current, external_folio: event.target.value }))} /> : <span className="block py-2 text-slate-600">{draft.external_folio || '-'}</span>}
      </td>
      <td className="px-3 py-2">
        {editing ? <input className={inputClass} value={draft.notes} onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))} /> : <span className="block py-2 text-slate-600">{draft.notes || '-'}</span>}
      </td>
      <td className="px-4 py-3 text-right">{money(remision.total)}</td>
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1">
          <button type="button" onClick={() => { setEditing(true); onSelect(); }} title="Editar" className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 text-slate-700 hover:bg-slate-50">
            <Pencil size={15} />
          </button>
          <button type="button" onClick={save} disabled={saving} title="Guardar" className="inline-flex h-8 w-8 items-center justify-center rounded bg-slate-900 text-white hover:bg-slate-800">
            <Save size={15} />
          </button>
          <button type="button" onClick={onPrint} title="Imprimir" className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 text-slate-700 hover:bg-slate-50">
            <Printer size={15} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function RemisionDetailEditor({
  detail,
  remisiones,
  selectedId,
  setSelectedId,
  reload,
  setNotice,
  onPrint,
}: {
  detail: RemisionDetail | null;
  remisiones: RemisionDoc[];
  selectedId: string;
  setSelectedId: (value: string) => void;
  reload: () => Promise<void>;
  setNotice: (value: string) => void;
  onPrint: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<RemisionDetail | null>(detail);

  useEffect(() => {
    setDraft(detail);
  }, [detail]);

  function patchHeader(patch: Partial<RemisionDoc>) {
    setDraft((current) => (current ? { ...current, remision: { ...current.remision, ...patch } } : current));
  }

  function patchItem(itemId: string, patch: Partial<RemisionItem>) {
    setDraft((current) => {
      if (!current) return current;
      return { ...current, items: current.items.map((item) => (item.id === itemId ? recalcItem({ ...item, ...patch }) : item)) };
    });
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    try {
      const res = await fetch('/api/remisiones', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: draft.remision.id,
          document_date: draft.remision.document_date,
          external_folio: draft.remision.external_folio || '',
          delivery_address: draft.remision.delivery_address || '',
          status: draft.remision.status,
          notes: draft.remision.notes || '',
          items: draft.items.map((item) => ({
            id: item.id,
            product_id: item.inventory_product_id || item.product_id,
            description: item.description,
            quantity: item.quantity,
            unit: item.unit,
            unit_price: item.unit_price,
            lot_code: item.lot_code,
            tax_rate: item.tax_rate,
          })),
        }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo guardar detalle');
      await reload();
      setNotice(`Remision actualizada: ${draft.remision.folio}`);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo guardar detalle');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded border border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Editar remision y renglones</h3>
          <p className="mt-0.5 text-xs text-slate-500">Encabezado, direccion, IVA, cantidades y precios ligados al kardex</p>
        </div>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="h-10 rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
          <option value="">Seleccionar remision</option>
          {remisiones.map((remision) => (
            <option key={remision.id} value={remision.id}>{remision.folio} - {remision.customer_name_snapshot}</option>
          ))}
        </select>
      </div>
      {draft ? (
        <div className="p-4">
          <div className="grid gap-3 lg:grid-cols-5">
            <Field label="Fecha" name="document_date" type="date" value={draft.remision.document_date || ''} onChange={(event) => patchHeader({ document_date: event.target.value })} />
            <Field label="Folio externo" name="external_folio" value={draft.remision.external_folio || ''} onChange={(event) => patchHeader({ external_folio: event.target.value })} />
            <label className="mt-3 block">
              <span className="text-xs font-medium text-slate-600">Estado</span>
              <select value={draft.remision.status || 'emitida'} onChange={(event) => patchHeader({ status: event.target.value })} className="mt-1 h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
                <option value="emitida">Emitida</option>
                <option value="pendiente">Pendiente</option>
                <option value="pagada">Pagada</option>
                <option value="cancelada">Cancelada</option>
              </select>
            </label>
            <Field label="Dir de entrega" name="delivery_address" value={draft.remision.delivery_address || ''} onChange={(event) => patchHeader({ delivery_address: event.target.value })} />
            <Field label="Notas" name="notes" value={draft.remision.notes || ''} onChange={(event) => patchHeader({ notes: event.target.value })} />
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-[980px] text-sm">
              <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-3 text-left">Producto / descripcion</th>
                  <th className="px-3 py-3 text-left">Lote</th>
                  <th className="px-3 py-3 text-right">Cantidad</th>
                  <th className="px-3 py-3 text-left">Unidad</th>
                  <th className="px-3 py-3 text-right">Precio</th>
                  <th className="px-3 py-3 text-right">IVA</th>
                  <th className="px-3 py-3 text-right">IVA $</th>
                  <th className="px-3 py-3 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {draft.items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100">
                    <td className="px-3 py-2"><input value={item.description || ''} onChange={(event) => patchItem(item.id, { description: event.target.value })} className="h-9 w-full rounded border border-slate-200 px-2 text-sm outline-none focus:border-slate-500" /></td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-600">{item.lot_code || 'GENERAL'}</td>
                    <td className="px-3 py-2"><input type="number" step="0.01" value={item.quantity || 0} onChange={(event) => patchItem(item.id, { quantity: Number(event.target.value) })} className="h-9 w-full rounded border border-slate-200 px-2 text-right text-sm outline-none focus:border-slate-500" /></td>
                    <td className="px-3 py-2"><input value={item.unit || ''} onChange={(event) => patchItem(item.id, { unit: event.target.value })} className="h-9 w-full rounded border border-slate-200 px-2 text-sm outline-none focus:border-slate-500" /></td>
                    <td className="px-3 py-2"><input type="number" step="0.01" value={item.unit_price || 0} onChange={(event) => patchItem(item.id, { unit_price: Number(event.target.value) })} className="h-9 w-full rounded border border-slate-200 px-2 text-right text-sm outline-none focus:border-slate-500" /></td>
                    <td className="px-3 py-2">
                      <select value={item.tax_rate || 0} onChange={(event) => patchItem(item.id, { tax_rate: Number(event.target.value) })} className="h-9 w-full rounded border border-slate-200 bg-white px-2 text-sm outline-none focus:border-slate-500">
                        <option value={0}>0%</option>
                        <option value={0.16}>16%</option>
                      </select>
                    </td>
                    <td className="px-3 py-3 text-right text-slate-500">{money(item.tax_amount)}</td>
                    <td className="px-3 py-3 text-right font-semibold text-slate-900">{money(item.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button type="button" onClick={onPrint} className="inline-flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              <Printer size={16} />
              Imprimir
            </button>
            <button type="button" onClick={save} disabled={saving} className="inline-flex h-10 items-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800">
              <Save size={16} />
              Guardar todo
            </button>
          </div>
        </div>
      ) : (
        <div className="px-4 py-8 text-center text-sm text-slate-500">Selecciona una remision</div>
      )}
    </section>
  );
}

function recalcItem(item: RemisionItem): RemisionItem {
  const quantity = Number(item.quantity || 0);
  const unit_price = Number(item.unit_price || 0);
  const tax_rate = Number(item.tax_rate || 0);
  const subtotal = Math.round(quantity * unit_price * 10000) / 10000;
  const tax_amount = Math.round(subtotal * tax_rate * 10000) / 10000;
  return { ...item, quantity, unit_price, tax_rate, tax_amount, line_total: Math.round((subtotal + tax_amount) * 100) / 100 };
}

function movementUnitCost(movement: KardexMovement): number {
  const metadata = movement.metadata || {};
  return Number(movement.unit_cost ?? metadata.lot_cost_snapshot ?? metadata.avg_cost_snapshot ?? 0);
}

function movementTotalCost(movement: KardexMovement): number {
  const stored = Number(movement.total_cost || 0);
  if (stored > 0) return stored;
  return movementUnitCost(movement) * Number(movement.quantity_out || movement.quantity_in || 0);
}

function movementNetAmount(movement: KardexMovement): number {
  const metadata = movement.metadata || {};
  const subtotal = Number(metadata.line_subtotal ?? metadata.subtotal_cost ?? 0);
  if (subtotal > 0) return subtotal;
  if (movement.source_type === 'remision') {
    return Math.round(Number(movement.unit_price || 0) * Number(movement.quantity_out || 0) * 100) / 100;
  }
  if (movement.source_type === 'compra') {
    return Math.max(Number(movement.total_cost || 0) - movementTaxAmount(movement), 0);
  }
  return Number(movement.total_sale || movement.total_cost || 0);
}

function movementTaxAmount(movement: KardexMovement): number {
  const metadata = movement.metadata || {};
  const taxAmount = Number(metadata.tax_amount ?? 0);
  if (taxAmount > 0) return taxAmount;
  if (movement.source_type === 'remision') {
    return Math.max(Number(movement.total_sale || 0) - movementNetAmount(movement), 0);
  }
  return 0;
}

function movementGrossAmount(movement: KardexMovement): number {
  if (movement.source_type === 'remision') return Number(movement.total_sale || 0);
  if (movement.source_type === 'compra') return Number(movement.total_cost || 0);
  return movementNetAmount(movement) + movementTaxAmount(movement);
}

function KeyProductMatrixPanel({
  matrix,
  startDate,
  endDate,
  setStartDate,
  setEndDate,
  loadMatrix,
}: {
  matrix: MatrixData | null;
  startDate: string;
  endDate: string;
  setStartDate: (value: string) => void;
  setEndDate: (value: string) => void;
  loadMatrix: () => Promise<void>;
}) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Ventas por productos clave</h3>
          <p className="mt-0.5 text-xs text-slate-500">Importe neto por remision y producto marcado como clave</p>
        </div>
        <div className="flex gap-2">
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
          <button type="button" onClick={loadMatrix} className="h-10 rounded bg-slate-900 px-3 text-sm font-semibold text-white">Ver</button>
        </div>
      </div>
      <KeyProductMatrix matrix={matrix} />
    </section>
  );
}

function KeyProductMatrix({ matrix }: { matrix: MatrixData | null }) {
  if (!matrix) return <div className="px-4 py-8 text-center text-sm text-slate-500">Carga un rango de fechas</div>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[980px] text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left">Remision</th>
            <th className="px-4 py-3 text-left">Fecha</th>
            <th className="px-4 py-3 text-left">Cliente</th>
            {matrix.products.map((product) => <th key={product.id} className="px-4 py-3 text-right">{product.product_name}</th>)}
            <th className="px-4 py-3 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row) => (
            <tr key={row.id} className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{row.folio}</td>
              <td className="px-4 py-3 text-slate-500">{row.document_date}</td>
              <td className="px-4 py-3 text-slate-600">{row.customer_name_snapshot}</td>
              {matrix.products.map((product) => <td key={product.id} className="px-4 py-3 text-right">{money(row.products[product.id])}</td>)}
              <td className="px-4 py-3 text-right font-semibold">{money(row.row_total)}</td>
            </tr>
          ))}
          <tr className="bg-slate-50 font-semibold">
            <td className="px-4 py-3" colSpan={3}>Totales</td>
            {matrix.products.map((product) => <td key={product.id} className="px-4 py-3 text-right">{money(matrix.totals[product.id])}</td>)}
            <td className="px-4 py-3 text-right">{money(matrix.grand_total)}</td>
          </tr>
          {matrix.rows.length === 0 && (
            <tr><td colSpan={matrix.products.length + 4} className="px-4 py-8 text-center text-sm text-slate-500">Sin ventas de productos clave en este rango</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function KardexTab({ products }: { products: Product[] }) {
  const [latest, setLatest] = useState<KardexMovement[]>([]);
  const [filtered, setFiltered] = useState<KardexMovement[]>([]);
  const [productId, setProductId] = useState(products[0]?.id || '');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadLatest();
  }, []);

  useEffect(() => {
    if (!productId && products[0]?.id) setProductId(products[0].id);
  }, [products, productId]);

  async function loadLatest() {
    try {
      const res = await fetch(`/api/kardex?limit=20&t=${Date.now()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo cargar kardex');
      setLatest(json.data || []);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo cargar kardex');
    }
  }

  async function loadFiltered() {
    if (!productId) {
      window.alert('Selecciona un producto');
      return;
    }
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      window.alert('Rango de fechas invalido');
      return;
    }
    if ((end.getTime() - start.getTime()) / 86400000 > 62) {
      window.alert('El rango maximo permitido es de 2 meses');
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams({ product_id: productId, start_date: startDate, end_date: endDate, limit: '500', t: String(Date.now()) });
      const res = await fetch(`/api/kardex?${params.toString()}`, { cache: 'no-store' });
      const json = await res.json();
      if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo cargar kardex filtrado');
      setFiltered(json.data || []);
    } catch (err: any) {
      window.alert(err.message || 'No se pudo cargar kardex filtrado');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Kardex por producto</h3>
            <p className="mt-0.5 text-xs text-slate-500">Un producto a la vez, rango maximo de 2 meses</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <select value={productId} onChange={(event) => setProductId(event.target.value)} className="h-10 min-w-64 rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
              <option value="">Seleccionar producto</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.product_name}</option>)}
            </select>
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="h-10 rounded border border-slate-200 px-3 text-sm" />
            <button type="button" onClick={loadFiltered} disabled={loading} className="h-10 rounded bg-slate-900 px-3 text-sm font-semibold text-white hover:bg-slate-800">Ver</button>
          </div>
        </div>
        <KardexTable movements={filtered} compact />
      </section>

      <section className="rounded border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Ultimos 20 movimientos</h3>
            <p className="mt-0.5 text-xs text-slate-500">Renglon por renglon de compras, remisiones y ajustes</p>
          </div>
          <button type="button" onClick={loadLatest} className="inline-flex h-9 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <RefreshCw size={15} />
            Actualizar
          </button>
        </div>
        <KardexTable movements={latest} />
      </section>
    </div>
  );
}

function KardexTable({ movements, compact }: { movements: KardexMovement[]; compact?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className={`${compact ? 'min-w-[1460px] text-xs' : 'min-w-[1360px] text-sm'}`}>
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3 text-left">Fecha</th>
            <th className="px-3 py-3 text-left">Documento</th>
            <th className="px-3 py-3 text-left">Tipo</th>
            <th className="px-3 py-3 text-left">Producto</th>
            <th className="px-3 py-3 text-left">Lote</th>
            <th className="px-3 py-3 text-left">Cliente/proveedor</th>
            <th className="px-3 py-3 text-right">Entrada</th>
            <th className="px-3 py-3 text-right">Salida</th>
            <th className="px-3 py-3 text-right">Saldo</th>
            <th className="px-3 py-3 text-right">Costo</th>
            <th className="px-3 py-3 text-right">Precio</th>
            <th className="px-3 py-3 text-right">Neto</th>
            <th className="px-3 py-3 text-right">IVA</th>
            <th className="px-3 py-3 text-right">Total</th>
            <th className="px-3 py-3 text-left">Pago</th>
            <th className="px-3 py-3 text-left">Notas</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((movement) => (
              <tr key={movement.id} className="border-b border-slate-100">
                <td className="px-3 py-2 text-slate-500">{movement.movement_date}</td>
                <td className="px-3 py-2 font-medium text-slate-900">{movement.source_folio || movement.folio}</td>
                <td className="px-3 py-2 text-slate-600">{movement.source_type}</td>
                <td className="px-3 py-2 text-slate-700">{movement.product_name_snapshot}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-600">{movement.lot_code || 'GENERAL'}</td>
                <td className="px-3 py-2 text-slate-500">{movement.customer_name_snapshot || movement.supplier_name_snapshot || '-'}</td>
                <td className="px-3 py-2 text-right">{qty(movement.quantity_in)}</td>
                <td className="px-3 py-2 text-right">{qty(movement.quantity_out)}</td>
                <td className="px-3 py-2 text-right">{qty(movement.balance_after)}</td>
                <td className="px-3 py-2 text-right">{money(movementUnitCost(movement))}</td>
                <td className="px-3 py-2 text-right">{money(movement.unit_price)}</td>
                <td className="px-3 py-2 text-right">{money(movementNetAmount(movement))}</td>
                <td className="px-3 py-2 text-right">{money(movementTaxAmount(movement))}</td>
                <td className="px-3 py-2 text-right">{money(movementGrossAmount(movement))}</td>
                <td className="px-3 py-2 text-slate-500">{movement.payment_status}</td>
                <td className="px-3 py-2 text-slate-500">{movement.notes || '-'}</td>
              </tr>
          ))}
          {movements.length === 0 && <tr><td colSpan={16} className="px-4 py-8 text-center text-sm text-slate-500">Sin movimientos</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function MovementTable({ movements, isSale }: { movements: KardexMovement[]; isSale: boolean }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <SectionTitle title={isSale ? 'Remisiones' : 'Compras'} subtitle={`${movements.length} movimientos`} />
      <div className="overflow-x-auto">
        <table className="min-w-[980px] text-sm">
          <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Folio</th>
              <th className="px-4 py-3 text-left">Fecha</th>
              <th className="px-4 py-3 text-left">Producto</th>
              <th className="px-4 py-3 text-left">Lote</th>
              <th className="px-4 py-3 text-left">{isSale ? 'Cliente' : 'Proveedor'}</th>
              <th className="px-4 py-3 text-right">Cantidad</th>
              <th className="px-4 py-3 text-right">Neto</th>
              <th className="px-4 py-3 text-right">IVA</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-right">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((movement) => (
              <tr key={movement.id} className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">{movement.source_folio}</td>
                <td className="px-4 py-3 text-slate-500">{movement.movement_date}</td>
                <td className="px-4 py-3 text-slate-700">{movement.product_name_snapshot}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{movement.lot_code || 'GENERAL'}</td>
                <td className="px-4 py-3 text-slate-500">{isSale ? movement.customer_name_snapshot : movement.supplier_name_snapshot}</td>
                <td className="px-4 py-3 text-right">{qty(isSale ? movement.quantity_out : movement.quantity_in)}</td>
                <td className="px-4 py-3 text-right">{money(movementNetAmount(movement))}</td>
                <td className="px-4 py-3 text-right">{money(movementTaxAmount(movement))}</td>
                <td className="px-4 py-3 text-right">{money(movementGrossAmount(movement))}</td>
                <td className="px-4 py-3 text-right">{money(movement.balance_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProductKardexTable({ movements }: { movements: KardexMovement[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3 text-left">Folio</th>
            <th className="px-4 py-3 text-left">Tipo</th>
            <th className="px-4 py-3 text-left">Fecha</th>
            <th className="px-4 py-3 text-left">Lote</th>
            <th className="px-4 py-3 text-right">Entrada</th>
            <th className="px-4 py-3 text-right">Salida</th>
            <th className="px-4 py-3 text-left">Origen</th>
            <th className="px-4 py-3 text-left">Notas</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((movement) => (
            <tr key={movement.id} className="border-b border-slate-100">
              <td className="px-4 py-3 font-medium text-slate-900">{movement.source_folio || movement.folio}</td>
              <td className="px-4 py-3 text-slate-600">{movement.source_type}</td>
              <td className="px-4 py-3 text-slate-500">{movement.movement_date}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-600">{movement.lot_code || 'GENERAL'}</td>
              <td className="px-4 py-3 text-right">{qty(movement.quantity_in)}</td>
              <td className="px-4 py-3 text-right">{qty(movement.quantity_out)}</td>
              <td className="px-4 py-3 text-slate-500">
                {movement.customer_name_snapshot || movement.supplier_name_snapshot || 'Manual'}
              </td>
              <td className="px-4 py-3 text-slate-500">{movement.notes || '-'}</td>
            </tr>
          ))}
          {movements.length === 0 && (
            <tr>
              <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-500">
                Sin movimientos para este producto
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function SectionTitle({ title, subtitle, compact = false }: { title: string; subtitle: string; compact?: boolean }) {
  return (
    <div className={`${compact ? 'mb-3' : 'border-b border-slate-200 px-4 py-3'}`}>
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
    </div>
  );
}

function Field(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string; name: string }) {
  const { label, ...inputProps } = props;
  return (
    <label className="mt-3 block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <input {...inputProps} className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
    </label>
  );
}

function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; name: string }) {
  const { label, ...textareaProps } = props;
  return (
    <label className="mt-3 block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <textarea {...textareaProps} className="mt-1 min-h-20 w-full rounded border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-500" />
    </label>
  );
}

function Select({ label, options, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; options: Array<{ value: string; label: string }> }) {
  return (
    <label className="mt-3 block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <select {...props} className="mt-1 h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
        <option value="">Seleccionar</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
