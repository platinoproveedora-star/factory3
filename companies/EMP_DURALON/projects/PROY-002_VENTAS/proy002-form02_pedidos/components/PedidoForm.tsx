'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { createPedido, getCustomers, getProducts, openPedidoPdf, today } from '@/lib/api';
import type { Customer, FormItem, Product } from '@/lib/api';
import projectContext from '@/project-context.json';

const IVA = 0.16;

const paymentMethods = [
  { value: 'credit', label: 'Credito' },
  { value: 'cash', label: 'Contado' },
  { value: 'transfer', label: 'Transferencia' },
  { value: 'check', label: 'Cheque' },
  { value: 'other', label: 'Otro' },
];

function mxn(value: number) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(value || 0);
}

function clean(value: string) {
  return value.trim().toLowerCase();
}

function newItem(): FormItem {
  return {
    _key: crypto.randomUUID(),
    product_id: null,
    description: '',
    quantity: 1,
    unit: 'pieza',
    unit_price_ex_vat: 0,
    vat_rate: IVA,
    weight_kg_per_unit: 0,
    weight_source: 'missing',
  };
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

export default function PedidoForm() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

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
  const [items, setItems] = useState<FormItem[]>([newItem()]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ folio: string; total: number; total_weight_kg: number } | null>(null);

  useEffect(() => {
    Promise.all([getCustomers(), getProducts()])
      .then(([customerRows, productRows]) => {
        setCustomers(customerRows);
        setProducts(productRows);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'No se pudo cargar catalogo'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (customerRef.current && !customerRef.current.contains(event.target as Node)) setCustomerOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filteredCustomers = useMemo(() => {
    const term = clean(customerQuery);
    const rows = term
      ? customers.filter((row) => clean(`${row.party_name} ${row.folio || ''} ${row.phone || ''}`).includes(term))
      : customers;
    return rows.slice(0, 20);
  }, [customers, customerQuery]);

  const subtotal = items.reduce((sum, item) => sum + lineSubtotal(item), 0);
  const taxTotal = items.reduce((sum, item) => sum + lineVat(item), 0);
  const total = Math.round((subtotal + taxTotal) * 100) / 100;
  const totalWeight = Math.round(items.reduce((sum, item) => sum + lineWeight(item), 0) * 10000) / 10000;
  const missingWeights = items.filter((item) => item.product_id && item.weight_source === 'missing').length;

  function selectCustomer(row: Customer) {
    setCustomer(row);
    setCustomerQuery(row.party_name);
    if (!deliveryAddress) setDeliveryAddress(row.address || '');
    setCustomerOpen(false);
  }

  function updateItem(key: string, patch: Partial<FormItem>) {
    setItems((current) => current.map((item) => (item._key === key ? { ...item, ...patch } : item)));
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
    setItems((current) => (current.length > 1 ? current.filter((item) => item._key !== key) : current));
  }

  function resetForm() {
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
    setItems([newItem()]);
    setError('');
    setResult(null);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    if (!customer) {
      setError('Selecciona un cliente de la lista.');
      return;
    }
    if (!dueDate) {
      setError('Fecha prometida requerida.');
      return;
    }
    if (items.some((item) => !item.description.trim() || item.quantity <= 0)) {
      setError('Cada producto necesita descripcion y cantidad mayor a 0.');
      return;
    }
    if (items.some((item) => item.unit_price_ex_vat < 0)) {
      setError('El precio no puede ser negativo.');
      return;
    }

    setSubmitting(true);
    try {
      const response = await createPedido({
        customer_id: customer.id,
        customer_name: customer.party_name,
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
      });
      setResult({
        folio: response.pedido.folio,
        total: response.pedido.total,
        total_weight_kg: response.pedido.total_weight_kg,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar pedido');
    } finally {
      setSubmitting(false);
    }
  }

  function preventImplicitSubmit(event: React.KeyboardEvent<HTMLFormElement>) {
    if (event.key !== 'Enter') return;
    const target = event.target as HTMLElement;
    if (target.tagName === 'TEXTAREA') return;
    event.preventDefault();
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-5">
        <p className="text-sm text-slate-500">Cargando catalogos...</p>
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

  if (result) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5">
        <section className="w-full max-w-sm rounded border border-slate-200 bg-white p-5 text-center shadow-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">Pedido guardado</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-emerald-700">{result.folio}</h1>
          <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <div className="rounded bg-slate-50 p-3">
              <p className="text-slate-500">Total</p>
              <p className="font-semibold text-slate-950">{mxn(result.total)}</p>
            </div>
            <div className="rounded bg-slate-50 p-3">
              <p className="text-slate-500">Peso</p>
              <p className="font-semibold text-slate-950">{result.total_weight_kg.toFixed(2)} kg</p>
            </div>
          </div>
          <button type="button" onClick={() => openPedidoPdf(result.folio)} className="mt-5 h-12 w-full rounded bg-slate-900 text-sm font-semibold text-white">
            Imprimir pedido
          </button>
          <button type="button" onClick={resetForm} className="mt-3 h-12 w-full rounded border border-slate-200 text-sm font-semibold text-slate-700">
            Nuevo pedido
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 pb-28">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto max-w-2xl">
          <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{projectContext.company_label} · {projectContext.project_label}</p>
          <h1 className="text-xl font-bold text-slate-950">Nuevo pedido</h1>
        </div>
      </header>

      <form id="pedido-form" onSubmit={submit} onKeyDown={preventImplicitSubmit} className="mx-auto max-w-2xl space-y-3 px-4 py-4">
        {error && <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-500">Cliente</h2>
          <div ref={customerRef} className="relative mt-3">
            <input
              value={customerQuery}
              onChange={(event) => {
                setCustomerQuery(event.target.value);
                setCustomer(null);
                setCustomerOpen(true);
              }}
              onFocus={() => setCustomerOpen(true)}
              placeholder="Buscar cliente activo"
              className="h-12 w-full rounded border border-slate-300 px-3 text-base outline-none focus:border-slate-700"
            />
            {customerOpen && !customer && (
              <div className="absolute z-40 mt-1 max-h-72 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg">
                <div className="border-b border-slate-100 px-3 py-2 text-xs text-slate-500">{customers.length} clientes activos</div>
                {filteredCustomers.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectCustomer(row)}
                    className="block w-full border-b border-slate-100 px-3 py-3 text-left last:border-b-0 hover:bg-slate-50"
                  >
                    <p className="font-semibold text-slate-900">{row.party_name}</p>
                    <p className="text-xs text-slate-500">{[row.folio, row.phone].filter(Boolean).join(' · ')}</p>
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
              <input type="date" value={documentDate} onChange={(event) => setDocumentDate(event.target.value)} className="input" />
            </Field>
            <Field label="Fecha prometida">
              <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="input" />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Forma de pago">
              <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} className="input bg-white">
                {paymentMethods.map((method) => (
                  <option key={method.value} value={method.value}>{method.label}</option>
                ))}
              </select>
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Direccion de entrega">
              <input value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} placeholder="Direccion" className="input" />
            </Field>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Ciudad">
              <input value={city} onChange={(event) => setCity(event.target.value)} placeholder="Ciudad" className="input" />
            </Field>
            <Field label="Cuadrante">
              <input value={cityQuadrant} onChange={(event) => setCityQuadrant(event.target.value)} placeholder="Norte, sur..." className="input" />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Folio externo">
              <input value={externalFolio} onChange={(event) => setExternalFolio(event.target.value)} placeholder="Opcional" className="input" />
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
              canRemove={items.length > 1}
              onRemove={() => removeItem(item._key)}
              onUpdate={(patch) => updateItem(item._key, patch)}
              onSelectProduct={(product) => selectProduct(item._key, product)}
            />
          ))}
          <button type="button" onClick={() => setItems((current) => [...current, newItem()])} className="flex h-12 w-full items-center justify-center rounded border border-dashed border-slate-300 bg-white text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50">
            Agregar producto
          </button>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <Field label="Notas">
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} placeholder="Observaciones del pedido" className="input h-auto py-2" />
          </Field>
          {missingWeights > 0 && (
            <p className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {missingWeights} producto(s) no tienen peso en catalogo. El pedido se guarda, pero logistica debe completar esa equivalencia.
            </p>
          )}
        </section>
      </form>

      <footer className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white px-4 py-3 shadow-[0_-8px_20px_rgba(15,23,42,0.08)]">
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-slate-950">{mxn(total)}</p>
            <p className="text-xs text-slate-500">Peso {totalWeight.toFixed(2)} kg · IVA {mxn(taxTotal)}</p>
          </div>
          <button type="submit" form="pedido-form" disabled={submitting} className="h-12 rounded bg-emerald-700 px-5 text-sm font-bold text-white disabled:opacity-50">
            {submitting ? 'Guardando' : 'Guardar'}
          </button>
        </div>
      </footer>
    </main>
  );
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
  canRemove,
  onRemove,
  onUpdate,
  onSelectProduct,
}: {
  item: FormItem;
  index: number;
  products: Product[];
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
    const rows = term
      ? products.filter((product) => clean(`${product.product_name} ${product.sku || ''} ${product.folio || ''}`).includes(term))
      : products;
    return rows.slice(0, 12);
  }, [products, query]);

  return (
    <article className="rounded border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Partida {index + 1}</p>
        {canRemove && (
          <button type="button" onClick={onRemove} className="rounded px-2 py-1 text-xs font-semibold text-red-600">
            Quitar
          </button>
        )}
      </div>
      <div ref={ref} className="relative">
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            onUpdate({ description: event.target.value, product_id: null, weight_kg_per_unit: 0, weight_source: 'missing' });
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Buscar producto"
          className="input"
        />
        {open && (
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
                <p className="text-xs text-slate-500">{[product.sku, product.unit, product.weight_kg ? `${Number(product.weight_kg).toFixed(2)} kg` : 'sin peso'].filter(Boolean).join(' · ')}</p>
              </button>
            ))}
            {!suggestions.length && <p className="px-3 py-3 text-sm text-slate-500">Sin coincidencias</p>}
          </div>
        )}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <Field label="Cantidad">
          <input type="number" min="0" step="0.01" value={item.quantity} onChange={(event) => onUpdate({ quantity: Number(event.target.value || 0) })} className="input" />
        </Field>
        <Field label="Unidad">
          <input value={item.unit} onChange={(event) => onUpdate({ unit: event.target.value })} className="input" />
        </Field>
        <Field label="IVA %">
          <input type="number" min="0" step="1" value={Math.round(item.vat_rate * 100)} onChange={(event) => onUpdate({ vat_rate: Number(event.target.value || 0) / 100 })} className="input" />
        </Field>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Field label="Precio sin IVA">
          <input type="number" min="0" step="0.0001" inputMode="decimal" value={item.unit_price_ex_vat} onChange={(event) => onUpdate({ unit_price_ex_vat: Number(event.target.value || 0) })} className="input" />
        </Field>
        <Field label="Precio con IVA">
          <input
            type="number"
            min="0"
            step="0.0001"
            inputMode="decimal"
            value={Math.round(item.unit_price_ex_vat * (1 + item.vat_rate) * 10000) / 10000}
            onChange={(event) => onUpdate({ unit_price_ex_vat: item.vat_rate <= -1 ? 0 : Math.round((Number(event.target.value || 0) / (1 + item.vat_rate)) * 10000) / 10000 })}
            className="input"
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
