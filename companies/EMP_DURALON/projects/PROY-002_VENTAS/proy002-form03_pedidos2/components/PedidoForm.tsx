'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  createPedido,
  editableStatus,
  emptyItem,
  getCustomers,
  getPedidoDetail,
  getPedidos,
  getProducts,
  openPedidoPdf,
  openRemisionPdf,
  pedidoToRemision,
  today,
  updatePedido,
} from '@/lib/api';
import type { Customer, FormItem, Pedido, PedidoItem, Product } from '@/lib/api';
import projectContext from '@/project-context.json';

const IVA = 0.16;

const paymentMethods = [
  { value: 'credit', label: 'Credito' },
  { value: 'cash', label: 'Contado' },
  { value: 'transfer', label: 'Transferencia' },
  { value: 'check', label: 'Cheque' },
  { value: 'other', label: 'Otro' },
];

const filters = [
  { value: 'active', label: 'Editables' },
  { value: 'liberado', label: 'Liberados' },
  { value: 'remisionado', label: 'Remisionados' },
  { value: 'all', label: 'Todos' },
];

function mxn(value: number) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(value || 0);
}

function clean(value: string) {
  return value.trim().toLowerCase();
}

function lineSubtotal(item: FormItem) {
  return Math.round(item.quantity * item.unit_price_ex_vat * 100) / 100;
}

function lineVat(item: FormItem) {
  return Math.round(lineSubtotal(item) * item.vat_rate * 100) / 100;
}

function lineTotal(item: FormItem) {
  return Math.round((lineSubtotal(item) + lineVat(item)) * 100) / 100;
}

function lineWeight(item: FormItem) {
  return Math.round(item.quantity * item.weight_kg_per_unit * 10000) / 10000;
}

function itemFromPedido(row: PedidoItem): FormItem {
  return {
    _key: crypto.randomUUID(),
    product_id: row.inventory_product_id || row.product_id || null,
    description: row.description || '',
    quantity: Number(row.quantity || 0),
    unit: row.unit || 'pieza',
    unit_price_ex_vat: Number(row.unit_price_ex_vat ?? row.unit_price ?? 0),
    vat_rate: Number(row.vat_rate ?? row.tax_rate ?? IVA),
    weight_kg_per_unit: Number(row.weight_kg_per_unit || 0),
    weight_source: Number(row.weight_kg_per_unit || 0) > 0 ? 'catalog' : 'missing',
  };
}

function remisionFolio(pedido: Pedido | null) {
  const meta = pedido?.metadata && typeof pedido.metadata === 'object' ? pedido.metadata : {};
  return String(meta?.remision_folio || meta?.converted_to_remision_folio || '');
}

export default function PedidoForm() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [filter, setFilter] = useState('active');
  const [search, setSearch] = useState('');

  const [current, setCurrent] = useState<Pedido | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [customerQuery, setCustomerQuery] = useState('');
  const [customerOpen, setCustomerOpen] = useState(false);
  const customerRef = useRef<HTMLDivElement>(null);

  const [documentDate, setDocumentDate] = useState(today());
  const [dueDate, setDueDate] = useState('');
  const [externalFolio, setExternalFolio] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('credit');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [city, setCity] = useState('');
  const [cityQuadrant, setCityQuadrant] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<FormItem[]>([emptyItem()]);

  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    Promise.all([getCustomers(), getProducts(), getPedidos()])
      .then(([customerRows, productRows, pedidoRows]) => {
        setCustomers(customerRows);
        setProducts(productRows);
        setPedidos(pedidoRows);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'No se pudo cargar catalogos'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (customerRef.current && !customerRef.current.contains(event.target as Node)) setCustomerOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const isEditable = editableStatus(current?.status);
  const selectedRemisionFolio = remisionFolio(current);
  const subtotal = items.reduce((sum, item) => sum + lineSubtotal(item), 0);
  const taxTotal = items.reduce((sum, item) => sum + lineVat(item), 0);
  const total = Math.round((subtotal + taxTotal) * 100) / 100;
  const totalWeight = Math.round(items.reduce((sum, item) => sum + lineWeight(item), 0) * 10000) / 10000;
  const missingWeights = items.filter((item) => item.product_id && item.weight_source === 'missing').length;

  const filteredPedidos = useMemo(() => {
    const term = clean(search);
    return pedidos
      .filter((pedido) => {
        if (filter === 'active') return pedido.status === 'pedido' || pedido.status === 'liberado';
        if (filter === 'all') return true;
        return pedido.status === filter;
      })
      .filter((pedido) => {
        if (!term) return true;
        return clean(`${pedido.folio} ${pedido.external_folio || ''} ${pedido.customer_name_snapshot} ${pedido.document_date}`).includes(term);
      })
      .slice(0, 30);
  }, [filter, pedidos, search]);

  const filteredCustomers = useMemo(() => {
    const term = clean(customerQuery);
    const rows = term ? customers.filter((row) => clean(`${row.party_name} ${row.folio || ''} ${row.phone || ''}`).includes(term)) : customers;
    return rows.slice(0, 20);
  }, [customers, customerQuery]);

  function preventImplicitSubmit(event: React.KeyboardEvent<HTMLFormElement>) {
    if (event.key !== 'Enter') return;
    const target = event.target as HTMLElement;
    if (target.tagName === 'TEXTAREA') return;
    event.preventDefault();
  }

  function selectCustomer(row: Customer) {
    setCustomer(row);
    setCustomerQuery(row.party_name);
    if (!deliveryAddress) setDeliveryAddress(row.address || '');
    setCustomerOpen(false);
  }

  function resetForm() {
    setCurrent(null);
    setCustomer(null);
    setCustomerQuery('');
    setDocumentDate(today());
    setDueDate('');
    setExternalFolio('');
    setPaymentMethod('credit');
    setDeliveryAddress('');
    setCity('');
    setCityQuadrant('');
    setNotes('');
    setItems([emptyItem()]);
    setError('');
    setNotice('');
  }

  async function refreshPedidos() {
    setPedidos(await getPedidos());
  }

  async function loadPedido(row: Pedido) {
    setError('');
    setNotice('');
    setBusy(`Cargando ${row.folio}`);
    try {
      const detail = await getPedidoDetail(row.folio);
      const pedido = detail.pedido;
      setCurrent(pedido);
      const selectedCustomer = customers.find((item) => item.id === pedido.customer_id) || null;
      setCustomer(selectedCustomer);
      setCustomerQuery(selectedCustomer?.party_name || pedido.customer_name_snapshot || '');
      setDocumentDate(pedido.document_date || today());
      setDueDate(pedido.due_date || '');
      setExternalFolio(pedido.external_folio || '');
      setPaymentMethod(pedido.payment_method || 'credit');
      setDeliveryAddress(pedido.delivery_address || '');
      setCity(pedido.city || '');
      setCityQuadrant(pedido.city_quadrant || '');
      setNotes(pedido.notes || '');
      setItems(detail.items.length ? detail.items.map(itemFromPedido) : [emptyItem()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar pedido');
    } finally {
      setBusy('');
    }
  }

  function updateItem(key: string, patch: Partial<FormItem>) {
    setItems((currentItems) => currentItems.map((item) => (item._key === key ? { ...item, ...patch } : item)));
  }

  function selectProduct(key: string, product: Product) {
    const weight = Number(product.weight_kg || 0);
    updateItem(key, {
      product_id: product.id,
      description: product.product_name,
      unit: product.unit || 'pieza',
      weight_kg_per_unit: weight,
      weight_source: weight > 0 ? 'catalog' : 'missing',
    });
  }

  function removeItem(key: string) {
    setItems((currentItems) => (currentItems.length > 1 ? currentItems.filter((item) => item._key !== key) : currentItems));
  }

  function validate() {
    if (!customer) return 'Selecciona un cliente de la lista.';
    if (!dueDate) return 'Fecha prometida requerida.';
    if (items.some((item) => !item.description.trim() || item.quantity <= 0)) return 'Cada producto necesita descripcion y cantidad mayor a 0.';
    if (items.some((item) => item.unit_price_ex_vat < 0)) return 'El precio no puede ser negativo.';
    return '';
  }

  function payload() {
    return {
      customer_id: customer?.id || '',
      customer_name: customer?.party_name,
      document_date: documentDate,
      due_date: dueDate,
      delivery_address: deliveryAddress || undefined,
      city: city || undefined,
      city_quadrant: cityQuadrant || undefined,
      payment_method: paymentMethod,
      external_folio: externalFolio || undefined,
      notes: notes || undefined,
      items: items.map((item) => ({
        product_id: item.product_id,
        description: item.description,
        quantity: item.quantity,
        unit: item.unit,
        unit_price_ex_vat: item.unit_price_ex_vat,
        vat_rate: item.vat_rate,
      })),
    };
  }

  async function savePedido() {
    setError('');
    setNotice('');
    if (!isEditable) {
      setError('Este pedido ya esta bloqueado.');
      return null;
    }
    const message = validate();
    if (message) {
      setError(message);
      return null;
    }
    setBusy(current ? 'Guardando cambios' : 'Guardando pedido');
    try {
      const response = current ? await updatePedido({ id: current.id, ...payload() }) : await createPedido(payload());
      const saved = response.pedido;
      setCurrent(saved);
      setNotice(`${saved.folio} guardado.`);
      await refreshPedidos();
      return saved;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar pedido');
      return null;
    } finally {
      setBusy('');
    }
  }

  async function createRemisionFromPedido() {
    setError('');
    setNotice('');
    if (!isEditable) {
      setError('Este pedido ya esta bloqueado.');
      return;
    }
    const saved = await savePedido();
    if (!saved?.id) return;
    const ok = window.confirm(`Crear remision desde ${saved.folio}? Esto descontara inventario y bloqueara el pedido.`);
    if (!ok) return;
    setBusy('Creando remision');
    try {
      const response = await pedidoToRemision({ pedido_id: saved.id, document_date: today(), notes });
      setCurrent(response.pedido);
      setNotice(`${saved.folio} remisionado con ${response.remision.folio}.`);
      await refreshPedidos();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear remision');
    } finally {
      setBusy('');
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-5">
        <p className="text-sm text-slate-500">Cargando pedidos...</p>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center px-5">
        <div className="w-full max-w-sm rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p className="font-semibold">No se pudo conectar con Factory3</p>
          <p className="mt-1">{loadError}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 pb-36">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto max-w-2xl">
          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{projectContext.company_label} / {projectContext.project_label}</p>
          <div className="mt-1 flex items-center justify-between gap-3">
            <h1 className="text-xl font-bold text-slate-950">Pedidos</h1>
            <button type="button" onClick={resetForm} className="h-9 rounded border border-slate-200 px-3 text-xs font-bold text-slate-700">
              Nuevo
            </button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-2xl px-4 pt-4">
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar pedido, cliente o folio" className="input h-12 text-base" />
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setFilter(item.value)}
              className={`h-10 shrink-0 rounded-full border px-4 text-sm font-semibold ${filter === item.value ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
          {filteredPedidos.map((pedido) => (
            <button
              key={pedido.id}
              type="button"
              onClick={() => loadPedido(pedido)}
              className={`w-64 shrink-0 rounded border bg-white p-3 text-left shadow-sm ${current?.id === pedido.id ? 'border-slate-900' : 'border-slate-200'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-mono text-sm font-bold text-slate-950">{pedido.folio}</p>
                <StatusPill status={pedido.status} />
              </div>
              <p className="mt-1 truncate text-sm font-semibold text-slate-800">{pedido.customer_name_snapshot}</p>
              <p className="mt-2 text-xs text-slate-500">Promesa {pedido.due_date || 'sin fecha'} / {mxn(Number(pedido.total || 0))}</p>
            </button>
          ))}
          {!filteredPedidos.length && <p className="py-4 text-sm text-slate-500">Sin pedidos en este filtro.</p>}
        </div>
      </section>

      <form
        onSubmit={(event) => event.preventDefault()}
        onKeyDown={preventImplicitSubmit}
        className="mx-auto max-w-2xl space-y-3 px-4 py-2"
      >
        {current && (
          <section className="rounded border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-lg font-bold text-slate-950">{current.folio}</p>
                {current.status === 'liberado' && <p className="mt-1 text-xs text-amber-700">Remision anterior cancelada. Puede volver a remisionarse.</p>}
                {selectedRemisionFolio && <p className="mt-1 text-xs text-slate-500">Ligado a {selectedRemisionFolio}</p>}
              </div>
              <StatusPill status={current.status} />
            </div>
            {!isEditable && <p className="mt-3 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">Documento bloqueado. No se puede modificar despues de remisionar.</p>}
          </section>
        )}

        {error && <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        {notice && <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</div>}

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-500">Cliente</h2>
          <div ref={customerRef} className="relative mt-3">
            <input
              value={customerQuery}
              disabled={!isEditable}
              onChange={(event) => {
                setCustomerQuery(event.target.value);
                setCustomer(null);
                setCustomerOpen(true);
              }}
              onFocus={() => setCustomerOpen(true)}
              placeholder="Buscar cliente activo"
              className="input h-12 text-base disabled:bg-slate-100"
            />
            {customerOpen && !customer && isEditable && (
              <div className="absolute z-40 mt-1 max-h-72 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg">
                {filteredCustomers.map((row) => (
                  <button key={row.id} type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => selectCustomer(row)} className="block w-full border-b border-slate-100 px-3 py-3 text-left last:border-b-0 hover:bg-slate-50">
                    <p className="font-semibold text-slate-900">{row.party_name}</p>
                    <p className="text-xs text-slate-500">{[row.folio, row.phone].filter(Boolean).join(' / ')}</p>
                  </button>
                ))}
                {!filteredCustomers.length && <p className="px-3 py-3 text-sm text-slate-500">Sin coincidencias</p>}
              </div>
            )}
          </div>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-500">Documento y entrega</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Fecha pedido">
              <input type="date" disabled={!isEditable} value={documentDate} onChange={(event) => setDocumentDate(event.target.value)} className="input disabled:bg-slate-100" />
            </Field>
            <Field label="Fecha prometida">
              <input type="date" disabled={!isEditable} value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="input disabled:bg-slate-100" />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Forma de pago">
              <select disabled={!isEditable} value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} className="input bg-white disabled:bg-slate-100">
                {paymentMethods.map((method) => <option key={method.value} value={method.value}>{method.label}</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Direccion de entrega">
              <input disabled={!isEditable} value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} placeholder="Direccion" className="input disabled:bg-slate-100" />
            </Field>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Ciudad">
              <input disabled={!isEditable} value={city} onChange={(event) => setCity(event.target.value)} placeholder="Ciudad" className="input disabled:bg-slate-100" />
            </Field>
            <Field label="Cuadrante">
              <input disabled={!isEditable} value={cityQuadrant} onChange={(event) => setCityQuadrant(event.target.value)} placeholder="Norte, sur..." className="input disabled:bg-slate-100" />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Folio externo">
              <input disabled={!isEditable} value={externalFolio} onChange={(event) => setExternalFolio(event.target.value)} placeholder="Opcional" className="input disabled:bg-slate-100" />
            </Field>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-500">Productos</h2>
          {items.map((item, index) => (
            <ProductCard
              key={item._key}
              item={item}
              index={index}
              products={products}
              disabled={!isEditable}
              canRemove={items.length > 1}
              onRemove={() => removeItem(item._key)}
              onUpdate={(patch) => updateItem(item._key, patch)}
              onSelectProduct={(product) => selectProduct(item._key, product)}
            />
          ))}
          {isEditable && (
            <button type="button" onClick={() => setItems((currentItems) => [...currentItems, emptyItem()])} className="flex h-12 w-full items-center justify-center rounded border border-dashed border-slate-300 bg-white text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50">
              Agregar producto
            </button>
          )}
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <Field label="Notas">
            <textarea disabled={!isEditable} value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} placeholder="Observaciones del pedido" className="input h-auto py-2 disabled:bg-slate-100" />
          </Field>
          {missingWeights > 0 && (
            <p className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {missingWeights} producto(s) no tienen peso en catalogo. El pedido se guarda, pero logistica debe completar esa equivalencia.
            </p>
          )}
        </section>
      </form>

      <footer className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white px-4 py-3 shadow-[0_-8px_20px_rgba(15,23,42,0.08)]">
        <div className="mx-auto max-w-2xl">
          <div className="mb-3 flex items-center gap-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-slate-950">{mxn(total)}</p>
              <p className="text-xs text-slate-500">Peso {totalWeight.toFixed(2)} kg / IVA {mxn(taxTotal)}</p>
            </div>
            {current && <button type="button" onClick={() => openPedidoPdf(current.folio)} className="h-10 rounded border border-slate-200 px-3 text-xs font-bold text-slate-700">PDF</button>}
            {selectedRemisionFolio && <button type="button" onClick={() => openRemisionPdf(selectedRemisionFolio)} className="h-10 rounded border border-slate-200 px-3 text-xs font-bold text-slate-700">Remision</button>}
          </div>
          {isEditable ? (
            <div className="grid grid-cols-2 gap-2">
              <button type="button" disabled={Boolean(busy)} onClick={savePedido} className="h-12 rounded border border-slate-300 text-sm font-bold text-slate-800 disabled:opacity-50">
                {busy ? busy : current ? 'Guardar cambios' : 'Generar pedido'}
              </button>
              <button type="button" disabled={Boolean(busy)} onClick={createRemisionFromPedido} className="h-12 rounded bg-emerald-700 text-sm font-bold text-white disabled:opacity-50">
                Generar remision
              </button>
            </div>
          ) : (
            <button type="button" disabled className="h-12 w-full rounded bg-slate-200 text-sm font-bold text-slate-500">
              Pedido bloqueado
            </button>
          )}
        </div>
      </footer>
    </main>
  );
}

function StatusPill({ status }: { status?: string }) {
  const label = status || 'nuevo';
  const tone = status === 'remisionado' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : status === 'liberado' ? 'bg-amber-50 text-amber-800 border-amber-200' : 'bg-slate-50 text-slate-700 border-slate-200';
  return <span className={`rounded-full border px-2 py-1 text-[11px] font-bold uppercase ${tone}`}>{label}</span>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>
      {children}
    </label>
  );
}

function ProductCard({
  item,
  index,
  products,
  disabled,
  canRemove,
  onRemove,
  onUpdate,
  onSelectProduct,
}: {
  item: FormItem;
  index: number;
  products: Product[];
  disabled: boolean;
  canRemove: boolean;
  onRemove: () => void;
  onUpdate: (patch: Partial<FormItem>) => void;
  onSelectProduct: (product: Product) => void;
}) {
  const [query, setQuery] = useState(item.description);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setQuery(item.description);
  }, [item.description]);

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const suggestions = useMemo(() => {
    const term = clean(query);
    const rows = term ? products.filter((product) => clean(`${product.product_name} ${product.sku || ''} ${product.folio || ''}`).includes(term)) : products;
    return rows.slice(0, 12);
  }, [products, query]);

  return (
    <article className="rounded border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Partida {index + 1}</p>
        {canRemove && !disabled && (
          <button type="button" onClick={onRemove} className="rounded px-2 py-1 text-xs font-semibold text-red-600">
            Quitar
          </button>
        )}
      </div>
      <div ref={ref} className="relative">
        <input
          value={query}
          disabled={disabled}
          onChange={(event) => {
            setQuery(event.target.value);
            onUpdate({ description: event.target.value, product_id: null, weight_kg_per_unit: 0, weight_source: 'missing' });
            setOpen(true);
          }}
          onFocus={() => !disabled && setOpen(true)}
          placeholder="Buscar producto"
          className="input disabled:bg-slate-100"
        />
        {open && !disabled && (
          <div className="absolute z-30 mt-1 max-h-60 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg">
            {suggestions.map((product) => (
              <button
                key={product.id}
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onSelectProduct(product);
                  setQuery(product.product_name);
                  setOpen(false);
                }}
                className="block w-full border-b border-slate-100 px-3 py-3 text-left last:border-b-0 hover:bg-slate-50"
              >
                <p className="font-semibold text-slate-900">{product.product_name}</p>
                <p className="text-xs text-slate-500">{[product.sku, product.unit, product.weight_kg ? `${Number(product.weight_kg).toFixed(2)} kg` : 'sin peso'].filter(Boolean).join(' / ')}</p>
              </button>
            ))}
            {!suggestions.length && <p className="px-3 py-3 text-sm text-slate-500">Sin coincidencias</p>}
          </div>
        )}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <Field label="Cantidad">
          <input disabled={disabled} type="number" min="0" step="0.01" value={item.quantity} onChange={(event) => onUpdate({ quantity: Number(event.target.value || 0) })} className="input disabled:bg-slate-100" />
        </Field>
        <Field label="Unidad">
          <input disabled={disabled} value={item.unit} onChange={(event) => onUpdate({ unit: event.target.value })} className="input disabled:bg-slate-100" />
        </Field>
        <Field label="IVA %">
          <input disabled={disabled} type="number" min="0" step="1" value={Math.round(item.vat_rate * 100)} onChange={(event) => onUpdate({ vat_rate: Number(event.target.value || 0) / 100 })} className="input disabled:bg-slate-100" />
        </Field>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Field label="Precio sin IVA">
          <input disabled={disabled} type="number" min="0" step="0.0001" inputMode="decimal" value={item.unit_price_ex_vat} onChange={(event) => onUpdate({ unit_price_ex_vat: Number(event.target.value || 0) })} className="input disabled:bg-slate-100" />
        </Field>
        <Field label="Precio con IVA">
          <input
            disabled={disabled}
            type="number"
            min="0"
            step="0.0001"
            inputMode="decimal"
            value={Math.round(item.unit_price_ex_vat * (1 + item.vat_rate) * 10000) / 10000}
            onChange={(event) => onUpdate({ unit_price_ex_vat: item.vat_rate <= -1 ? 0 : Math.round((Number(event.target.value || 0) / (1 + item.vat_rate)) * 10000) / 10000 })}
            className="input disabled:bg-slate-100"
          />
        </Field>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 rounded bg-slate-50 p-2 text-xs">
        <div>
          <p className="text-slate-500">Subtotal</p>
          <p className="font-semibold">{mxn(lineSubtotal(item))}</p>
        </div>
        <div>
          <p className="text-slate-500">Peso</p>
          <p className="font-semibold">{lineWeight(item).toFixed(2)} kg</p>
        </div>
        <div>
          <p className="text-slate-500">Total</p>
          <p className="font-semibold">{mxn(lineTotal(item))}</p>
        </div>
      </div>
    </article>
  );
}
