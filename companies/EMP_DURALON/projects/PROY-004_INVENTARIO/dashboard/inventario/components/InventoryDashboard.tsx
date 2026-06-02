'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Boxes,
  Building2,
  CircleDollarSign,
  PackagePlus,
  RefreshCw,
  Save,
  Search,
  Store,
  Truck,
  UserRoundPlus,
} from 'lucide-react';
import { loadDashboardData, type DashboardData } from '../lib/client-data';
import { money, qty, type KardexMovement, type Party, type Product } from '../lib/supabase';

type Tab = 'inventario' | 'producto' | 'proveedores' | 'clientes' | 'ventas' | 'compras';

const emptyData: DashboardData = {
  products: [],
  customers: [],
  suppliers: [],
  purchases: [],
  sales: [],
  adjustments: [],
  stock: [],
  receivables_total: 0,
  payables_total: 0,
};

const tabs: Array<{ id: Tab; label: string; icon: any }> = [
  { id: 'inventario', label: 'Inventario', icon: Boxes },
  { id: 'producto', label: 'Producto', icon: PackagePlus },
  { id: 'proveedores', label: 'Proveedores', icon: Truck },
  { id: 'clientes', label: 'Clientes', icon: Store },
  { id: 'ventas', label: 'Ventas / salidas', icon: ArrowUpFromLine },
  { id: 'compras', label: 'Compras / entradas', icon: ArrowDownToLine },
];

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
      setData(await loadDashboardData());
    } catch (err: any) {
      setError(err.message || 'No se pudo cargar el dashboard');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

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

          {activeTab === 'inventario' && <InventoryTab products={filteredProducts} stock={data.stock} movements={[...data.sales, ...data.purchases, ...data.adjustments]} />}
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
          {activeTab === 'ventas' && (
            <MovementTab
              type="remision"
              products={data.products}
              parties={data.customers}
              movements={data.sales}
              saving={saving}
              setSaving={setSaving}
              refresh={refresh}
              setNotice={setNotice}
            />
          )}
          {activeTab === 'compras' && (
            <MovementTab
              type="compra"
              products={data.products}
              parties={data.suppliers}
              movements={data.purchases}
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
  refresh: () => Promise<void>;
  setNotice: (value: string) => void;
}) {
  const [selectedProductId, setSelectedProductId] = useState('');
  const selectedProduct = products.find((product) => product.id === selectedProductId) || products[0];
  const productId = selectedProduct?.id || '';
  const productStock = stock.find((row) => row.product_id === productId);
  const productMovements = movements
    .filter((movement) => movement.product_id === productId)
    .sort((a, b) => String(b.movement_date).localeCompare(String(a.movement_date)));

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
    <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
      <div className="space-y-5">
        <form onSubmit={saveProduct} className="rounded border border-slate-200 bg-white p-4">
          <SectionTitle title="Agregar producto" subtitle="Alta de catalogo" compact />
          <Field name="product_name" label="Nombre" required />
          <Field name="product_key" label="Clave interna" />
          <Field name="sku" label="SKU" />
          <Field name="category" label="Categoria" />
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

function InventoryTab({ products, stock, movements }: { products: Product[]; stock: DashboardData['stock']; movements: KardexMovement[] }) {
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
  refresh: () => Promise<void>;
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
  refresh: () => Promise<void>;
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

function PartyTable({ parties, refresh, setNotice }: { parties: Party[]; refresh: () => Promise<void>; setNotice: (value: string) => void }) {
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

function PartyRow({ party, refresh, setNotice }: { party: Party; refresh: () => Promise<void>; setNotice: (value: string) => void }) {
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
        body: JSON.stringify({ id: party.id, ...draft }),
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

function MovementTable({ movements, isSale }: { movements: KardexMovement[]; isSale: boolean }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <SectionTitle title={isSale ? 'Remisiones' : 'Compras'} subtitle={`${movements.length} movimientos`} />
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Folio</th>
              <th className="px-4 py-3 text-left">Fecha</th>
              <th className="px-4 py-3 text-left">Producto</th>
              <th className="px-4 py-3 text-left">{isSale ? 'Cliente' : 'Proveedor'}</th>
              <th className="px-4 py-3 text-right">Cantidad</th>
              <th className="px-4 py-3 text-right">Importe</th>
              <th className="px-4 py-3 text-right">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((movement) => (
              <tr key={movement.id} className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">{movement.source_folio}</td>
                <td className="px-4 py-3 text-slate-500">{movement.movement_date}</td>
                <td className="px-4 py-3 text-slate-700">{movement.product_name_snapshot}</td>
                <td className="px-4 py-3 text-slate-500">{isSale ? movement.customer_name_snapshot : movement.supplier_name_snapshot}</td>
                <td className="px-4 py-3 text-right">{qty(isSale ? movement.quantity_out : movement.quantity_in)}</td>
                <td className="px-4 py-3 text-right">{money(isSale ? movement.total_sale : movement.total_cost)}</td>
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
              <td colSpan={7} className="px-4 py-8 text-center text-sm text-slate-500">
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
