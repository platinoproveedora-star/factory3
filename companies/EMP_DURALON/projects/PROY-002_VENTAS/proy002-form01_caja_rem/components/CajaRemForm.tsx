'use client';

import { useEffect, useRef, useState } from 'react';
import { createRemision, getCustomers, getProductLots, getProducts, getRemisiones, openRemisionPdf } from '@/lib/api';
import type { Customer, FormItem, Product, Remision } from '@/lib/api';
import projectContext from '@/project-context.json';

const IVA = 0.16;

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(n);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function newItem(): FormItem {
  return { _key: crypto.randomUUID(), product_id: null, lot_code: null, lots: [], requires_lot: false, lots_loading: false, description: '', quantity: 1, unit: 'pieza', unit_price: 0, tax_rate: IVA, tax_amount: 0, line_total: 0 };
}

function calcItem(item: FormItem): FormItem {
  const sub   = Math.round(item.quantity * item.unit_price * 10000) / 10000;
  const tax   = Math.round(sub * item.tax_rate * 10000) / 10000;
  return { ...item, tax_amount: tax, line_total: Math.round((sub + tax) * 100) / 100 };
}

export default function CajaRemForm() {
  const [customers, setCustomers]     = useState<Customer[]>([]);
  const [products, setProducts]       = useState<Product[]>([]);
  const [remisiones, setRemisiones]   = useState<Remision[]>([]);
  const [loading, setLoading]         = useState(true);
  const [loadError, setLoadError]     = useState('');

  const [customer, setCustomer]       = useState<Customer | null>(null);
  const [custQuery, setCustQuery]     = useState('');
  const [custOpen, setCustOpen]       = useState(false);
  const custRef                        = useRef<HTMLDivElement>(null);

  const [docDate, setDocDate]         = useState(today());
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [extFolio, setExtFolio]       = useState('');
  const [notes, setNotes]             = useState('');
  const [items, setItems]             = useState<FormItem[]>([newItem()]);

  const [submitting, setSubmitting]   = useState(false);
  const [result, setResult]           = useState<{ folio: string; total: number } | null>(null);
  const [error, setError]             = useState('');

  // Load catalog
  useEffect(() => {
    Promise.all([getCustomers(), getProducts(), getRemisiones()])
      .then(([c, p, r]) => { setCustomers(c); setProducts(p); setRemisiones(r); setLoading(false); })
      .catch(e => { setLoadError(e.message); setLoading(false); });
  }, []);

  // Close customer dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (custRef.current && !custRef.current.contains(e.target as Node)) setCustOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filteredCusts = custQuery.length > 0
    ? customers.filter(c => c.party_name.toLowerCase().includes(custQuery.toLowerCase()))
    : customers;

  const filteredProds = (query: string) =>
    products.filter(p => p.product_name.toLowerCase().includes(query.toLowerCase()) || (p.sku ?? '').toLowerCase().includes(query.toLowerCase()));

  // Item helpers
  function updateItem(key: string, patch: Partial<FormItem>) {
    setItems(prev => prev.map(it => it._key === key ? calcItem({ ...it, ...patch }) : it));
  }

  function selectProduct(key: string, prod: Product) {
    setError('');
    setItems(prev => prev.map(it => it._key === key ? calcItem({
      ...it,
      product_id: prod.id,
      lot_code: null,
      lots: [],
      requires_lot: false,
      lots_loading: true,
      description: prod.product_name,
      unit: prod.unit,
      unit_price: prod.unit_price ?? it.unit_price,
    }) : it));

    getProductLots(prod.id)
      .then(data => {
        setItems(prev => prev.map(it => it._key === key ? calcItem({
          ...it,
          lots: data.lots,
          requires_lot: data.requires_lot,
          lot_code: data.default_lot_code ?? null,
          lots_loading: false,
        }) : it));
      })
      .catch(e => {
        setItems(prev => prev.map(it => it._key === key ? { ...it, lots_loading: false } : it));
        setError(`No se pudieron cargar lotes de ${prod.product_name}: ${e.message ?? e}`);
      });
  }

  function removeItem(key: string) {
    setItems(prev => prev.length > 1 ? prev.filter(it => it._key !== key) : prev);
  }

  // Totals
  const subtotal  = items.reduce((s, it) => s + Math.round(it.quantity * it.unit_price * 100) / 100, 0);
  const taxTotal  = items.reduce((s, it) => s + it.tax_amount, 0);
  const total     = Math.round((subtotal + taxTotal) * 100) / 100;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const typedCustomer = custQuery.trim();
    if (!customer && !typedCustomer) { setError('Selecciona o escribe un cliente'); return; }
    if (items.some(it => !it.description || it.quantity <= 0)) { setError('Todos los productos necesitan descripción y cantidad mayor a 0'); return; }
    if (items.some(it => it.product_id && it.requires_lot && !it.lot_code)) { setError('Selecciona lote en los productos que tienen mas de un lote disponible'); return; }

    setSubmitting(true);
    try {
      const res = await createRemision({
        customer_id:   customer?.id,
        customer_name: customer ? undefined : typedCustomer,
        document_date: docDate,
        delivery_address: deliveryAddress || undefined,
        external_folio: extFolio || undefined,
        notes: notes || undefined,
        items: items.map(it => ({
          product_id:  it.product_id,
          lot_code:    it.lot_code,
          description: it.description,
          quantity:    it.quantity,
          unit:        it.unit,
          unit_price:  it.unit_price,
          tax_rate:    it.tax_rate,
        })),
      });
      setResult({ folio: res.folio, total: res.total });
      const rem = await getRemisiones(20);
      setRemisiones(rem);
    } catch (err: any) {
      setError(err.message ?? 'Error al crear remisión');
    } finally {
      setSubmitting(false);
    }
  }

  function handleNueva() {
    setResult(null);
    setError('');
    setCustomer(null);
    setCustQuery('');
    setDocDate(today());
    setDeliveryAddress('');
    setExtFolio('');
    setNotes('');
    setItems([newItem()]);
  }

  if (loading) return (
    <div className="flex h-screen items-center justify-center">
      <p className="text-slate-400 text-sm">Cargando catálogo…</p>
    </div>
  );

  if (loadError) return (
    <div className="flex h-screen items-center justify-center p-8">
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
        <p className="font-semibold text-red-700 mb-1">Error al conectar con Factory3</p>
        <p className="text-red-600 text-sm">{loadError}</p>
        <p className="text-slate-500 text-xs mt-3">Verifica que factory3 esté corriendo en {process.env.NEXT_PUBLIC_FACTORY_API_URL}</p>
      </div>
    </div>
  );

  // ── Success screen ────────────────────────────────────────────────────────
  if (result) return (
    <div className="flex h-screen items-center justify-center p-8">
      <div className="bg-white border border-slate-200 rounded-2xl p-10 max-w-sm w-full text-center shadow-sm">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Remisión emitida</h2>
        <p className="text-3xl font-mono font-bold text-emerald-600 my-4">{result.folio}</p>
        <p className="text-slate-500 mb-6">Total: <span className="font-semibold text-slate-800">{mxn(result.total)}</span></p>
        <button onClick={() => openRemisionPdf(result.folio)} className="mb-3 w-full border border-slate-300 text-slate-800 py-3 rounded-xl font-semibold hover:bg-slate-50 transition">
          Abrir PDF
        </button>
        <button onClick={handleNueva} className="w-full bg-slate-900 text-white py-3 rounded-xl font-semibold hover:bg-slate-700 transition">
          + Nueva Remisión
        </button>
      </div>
    </div>
  );

  // ── Form ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400">{projectContext.company_label} · {projectContext.project_label}</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">🧾 Nueva Remisión</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">

          {/* Cliente + Fecha + Folio externo */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
            <h2 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">Datos del documento</h2>

            {/* Cliente */}
            <div ref={custRef} className="relative">
              <label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label>
              <input
                type="text"
                value={customer ? customer.party_name : custQuery}
                onChange={e => { setCustQuery(e.target.value); setCustomer(null); setCustOpen(true); }}
                onFocus={() => setCustOpen(true)}
                placeholder="Buscar cliente…"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
              />
              {custOpen && filteredCusts.length > 0 && !customer && (
                <ul className="absolute z-20 w-full bg-white border border-slate-200 rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto">
                  {filteredCusts.slice(0, 20).map(c => (
                    <li key={c.id}
                        onClick={() => { setCustomer(c); setCustQuery(c.party_name); if (!deliveryAddress) setDeliveryAddress(c.address || ''); setCustOpen(false); }}
                        className="px-4 py-2 text-sm hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-0">
                      <span className="font-medium">{c.party_name}</span>
                      {c.phone && <span className="text-slate-400 ml-2 text-xs">{c.phone}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
                <input type="date" value={docDate} onChange={e => setDocDate(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Folio externo <span className="text-slate-400 font-normal">(opcional)</span></label>
                <input type="text" value={extFolio} onChange={e => setExtFolio(e.target.value)} placeholder="A-0001"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Dir de entrega <span className="text-slate-400 font-normal">(opcional)</span></label>
              <input type="text" value={deliveryAddress} onChange={e => setDeliveryAddress(e.target.value)} placeholder="Direccion donde se entrega la remision"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Notas <span className="text-slate-400 font-normal">(opcional)</span></label>
              <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Observaciones…"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400" />
            </div>
          </div>

          {/* Productos */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-700 text-sm uppercase tracking-wide mb-4">Productos</h2>

            <div className="space-y-3">
              {items.map((item, idx) => (
                <ItemRow key={item._key} item={item} idx={idx}
                  products={products} filteredProds={filteredProds}
                  onUpdate={patch => updateItem(item._key, patch)}
                  onSelectProduct={prod => selectProduct(item._key, prod)}
                  onRemove={() => removeItem(item._key)}
                  canRemove={items.length > 1} />
              ))}
            </div>

            <button type="button" onClick={() => setItems(prev => [...prev, newItem()])}
              className="mt-4 flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 border border-dashed border-slate-300 rounded-lg px-4 py-2 w-full justify-center hover:border-slate-400 transition">
              + Agregar producto
            </button>
          </div>

          {/* Totales */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="flex justify-between text-sm text-slate-600 mb-1">
              <span>Subtotal</span><span>{mxn(subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm text-slate-600 mb-3">
              <span>IVA 16%</span><span>{mxn(taxTotal)}</span>
            </div>
            <div className="flex justify-between text-lg font-bold text-slate-900 pt-3 border-t border-slate-200">
              <span>Total</span><span>{mxn(total)}</span>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button type="submit" disabled={submitting}
            className="w-full bg-slate-900 text-white py-4 rounded-2xl font-bold text-base hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition">
            {submitting ? 'Guardando…' : '🧾 Emitir Remisión'}
          </button>
        </form>

        {/* Remisiones recientes */}
        {remisiones.length > 0 && (
          <div className="mt-10">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-400 mb-3">Remisiones recientes</h2>
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              {remisiones.slice(0, 10).map((r, i) => (
                <div key={r.id} className={`flex items-center justify-between px-5 py-3 text-sm ${i > 0 ? 'border-t border-slate-100' : ''}`}>
                  <div>
                    <span className="font-mono font-semibold text-slate-800">{r.folio}</span>
                    {r.external_folio && <span className="text-slate-400 ml-2">({r.external_folio})</span>}
                    <span className="text-slate-500 ml-3">{r.customer_name_snapshot}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold">{mxn(r.total)}</span>
                    <span className="text-slate-400 ml-3 text-xs">{r.document_date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// ── Item Row ─────────────────────────────────────────────────────────────────

type ItemRowProps = {
  item: FormItem; idx: number;
  products: Product[];
  filteredProds: (q: string) => Product[];
  onUpdate: (patch: Partial<FormItem>) => void;
  onSelectProduct: (p: Product) => void;
  onRemove: () => void;
  canRemove: boolean;
};

function ItemRow({ item, idx, products, filteredProds, onUpdate, onSelectProduct, onRemove, canRemove }: ItemRowProps) {
  const [prodQuery, setProdQuery] = useState(item.description);
  const [prodOpen, setProdOpen]   = useState(false);
  const rowRef                     = useRef<HTMLDivElement>(null);
  const suggestions                = prodQuery.length > 0 ? filteredProds(prodQuery).slice(0, 10) : products.slice(0, 10);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (rowRef.current && !rowRef.current.contains(e.target as Node)) setProdOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Sync description back if parent changes it
  useEffect(() => { setProdQuery(item.description); }, [item.description]);

  return (
    <div ref={rowRef} className="border border-slate-200 rounded-xl p-3 bg-slate-50">
      <div className="flex items-start gap-2 mb-2">
        <span className="text-xs text-slate-400 font-mono pt-2 w-5 shrink-0">{idx + 1}</span>

        {/* Producto */}
        <div className="relative flex-1">
          <input
            type="text" value={prodQuery}
            onChange={e => { setProdQuery(e.target.value); onUpdate({ description: e.target.value, product_id: null, lot_code: null, lots: [], requires_lot: false, lots_loading: false }); setProdOpen(true); }}
            onFocus={() => setProdOpen(true)}
            placeholder="Producto o descripción…"
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          {prodOpen && suggestions.length > 0 && (
            <ul className="absolute z-20 w-full bg-white border border-slate-200 rounded-lg shadow-lg mt-1 max-h-40 overflow-y-auto">
              {suggestions.map(p => (
                <li key={p.id}
                    onClick={() => { onSelectProduct(p); setProdQuery(p.product_name); setProdOpen(false); }}
                    className="px-3 py-2 text-sm hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-0">
                  <span className="font-medium">{p.product_name}</span>
                  <span className="text-slate-400 ml-2">{p.unit} · {new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(p.unit_price ?? 0)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {canRemove && (
          <button type="button" onClick={onRemove} className="text-slate-400 hover:text-red-500 pt-2 text-lg leading-none">×</button>
        )}
      </div>

      {item.product_id && (
        <div className="ml-7 mb-2">
          <label className="text-xs text-slate-400">Lote</label>
          {item.lots_loading ? (
            <div className="mt-1 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-400 bg-white">
              Cargando lotes...
            </div>
          ) : item.lots.length > 0 ? (
            <select
              value={item.lot_code ?? ''}
              onChange={e => onUpdate({ lot_code: e.target.value || null })}
              required={item.requires_lot}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              <option value="" disabled={item.requires_lot}>
                {item.requires_lot ? 'Selecciona lote' : 'Sin lote especifico'}
              </option>
              {item.lots.map(lot => (
                <option key={lot.lot_code} value={lot.lot_code}>{lot.label}</option>
              ))}
            </select>
          ) : (
            <div className="mt-1 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-400 bg-white">
              Sin lotes disponibles
            </div>
          )}
          {item.requires_lot && !item.lot_code && (
            <p className="mt-1 text-xs text-amber-700">Este producto tiene varios lotes; elige cual sale.</p>
          )}
        </div>
      )}

      {/* Qty / Unit / Price / IVA */}
      <div className="flex gap-2 ml-7">
        <div className="w-20">
          <label className="text-xs text-slate-400">Cant.</label>
          <input type="number" min="0" step="any" value={item.quantity}
            onChange={e => onUpdate({ quantity: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400" />
        </div>
        <div className="w-20">
          <label className="text-xs text-slate-400">Unidad</label>
          <input type="text" value={item.unit} onChange={e => onUpdate({ unit: e.target.value })}
            className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400" />
        </div>
        <div className="w-28">
          <label className="text-xs text-slate-400">Precio unit.</label>
          <input type="number" min="0" step="any" value={item.unit_price}
            onChange={e => onUpdate({ unit_price: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400" />
        </div>
        <div className="w-20">
          <label className="text-xs text-slate-400">IVA</label>
          <select value={item.tax_rate} onChange={e => onUpdate({ tax_rate: parseFloat(e.target.value) })}
            className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-400">
            <option value={0.16}>16%</option>
            <option value={0}>0%</option>
          </select>
        </div>
        <div className="flex-1 text-right pt-5">
          <span className="font-semibold text-slate-800 text-sm">
            {new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(item.line_total)}
          </span>
        </div>
      </div>
    </div>
  );
}
