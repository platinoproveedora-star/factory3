'use client';

import { useEffect, useMemo, useState } from 'react';
import { Banknote, CheckCircle2, FileUp, Loader2, RefreshCw, Search, WalletCards } from 'lucide-react';
import {
  applyPayment,
  createCollectionFolio,
  createPayment,
  getAccounts,
  getCustomers,
  getRemisiones,
  prepareReceiptUpload,
  todayIso,
  uploadReceipt,
  type Customer,
  type MoneyAccount,
  type Remision,
} from '@/lib/api';
import projectContext from '../project-context.json';

const paymentMethods = [
  { value: 'cash', label: 'Efectivo' },
  { value: 'transfer', label: 'Transferencia' },
  { value: 'deposit', label: 'Deposito' },
  { value: 'card', label: 'Tarjeta' },
  { value: 'check', label: 'Cheque' },
  { value: 'other', label: 'Otro' },
];

function money(value: number | string | null | undefined) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(value || 0));
}

function cleanText(value: string) {
  return value.trim().toLowerCase();
}

function balance(remision: Remision) {
  return Number(remision.balance_total ?? remision.total ?? 0);
}

function allocate(remisiones: Remision[], selectedIds: string[], amount: number) {
  let remaining = Number(amount || 0);
  const rows: Array<{ remision: Remision; amount: number }> = [];
  for (const id of selectedIds) {
    if (remaining <= 0) break;
    const remision = remisiones.find((row) => row.id === id);
    if (!remision) continue;
    const applied = Math.min(remaining, balance(remision));
    if (applied > 0) rows.push({ remision, amount: Number(applied.toFixed(2)) });
    remaining = Number((remaining - applied).toFixed(2));
  }
  return rows;
}

export default function PaymentCaptureForm() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [accounts, setAccounts] = useState<MoneyAccount[]>([]);
  const [remisiones, setRemisiones] = useState<Remision[]>([]);
  const [customerSearch, setCustomerSearch] = useState('');
  const [customerOpen, setCustomerOpen] = useState(false);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [amount, setAmount] = useState('');
  const [accountId, setAccountId] = useState('');
  const [selectedRemisiones, setSelectedRemisiones] = useState<string[]>([]);
  const [bankName, setBankName] = useState('');
  const [reference, setReference] = useState('');
  const [trackingKey, setTrackingKey] = useState('');
  const [paymentDate, setPaymentDate] = useState(todayIso());
  const [notes, setNotes] = useState('');
  const [receipt, setReceipt] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const companyLabel = projectContext.company_label || projectContext.company_id;
  const needsBankFields = paymentMethod === 'transfer' || paymentMethod === 'deposit';
  const amountNumber = Number(amount || 0);
  const allocated = useMemo(() => allocate(remisiones, selectedRemisiones, amountNumber), [remisiones, selectedRemisiones, amountNumber]);
  const selectedTotal = allocated.reduce((sum, row) => sum + row.amount, 0);
  const unappliedPreview = Math.max(amountNumber - selectedTotal, 0);
  const filteredCustomers = useMemo(() => {
    const term = cleanText(customerSearch);
    if (!term) return customers.slice(0, 8);
    return customers
      .filter((row) => cleanText(`${row.party_name} ${row.folio || ''} ${row.phone || ''}`).includes(term))
      .slice(0, 12);
  }, [customers, customerSearch]);

  async function refreshBase() {
    setLoading(true);
    setError('');
    try {
      const [customerRows, accountRows] = await Promise.all([getCustomers(), getAccounts()]);
      setCustomers(customerRows);
      setAccounts(accountRows);
      if (!accountId && accountRows[0]) setAccountId(accountRows[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar catalogos');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshBase();
  }, []);

  useEffect(() => {
    if (!customer) {
      setRemisiones([]);
      setSelectedRemisiones([]);
      return;
    }
    setError('');
    getRemisiones(customer.id)
      .then((rows) => {
        setRemisiones(rows);
        setSelectedRemisiones((current) => current.filter((id) => rows.some((row) => row.id === id)));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar remisiones'));
  }, [customer]);

  function selectCustomer(row: Customer) {
    setCustomer(row);
    setCustomerSearch(row.party_name);
    setCustomerOpen(false);
    setNotice('');
  }

  function toggleRemision(id: string) {
    setSelectedRemisiones((current) => (current.includes(id) ? current.filter((row) => row !== id) : [...current, id]));
  }

  async function submit() {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      if (!customer) throw new Error('Cliente requerido');
      if (amountNumber <= 0) throw new Error('Importe debe ser mayor a 0');
      if (!accountId) throw new Error('Cuenta destino requerida');
      if (needsBankFields && !bankName.trim()) throw new Error('Banco requerido para transferencia o deposito');

      let receiptFields: Record<string, string> = {};
      if (receipt) {
        const prepared = await prepareReceiptUpload(receipt);
        await uploadReceipt(receipt, prepared);
        receiptFields = {
          receipt_file_bucket: prepared.bucket,
          receipt_file_path: prepared.path,
          ocr_status: 'pending',
          validation_status: 'pending',
        };
      }

      let collectionFolioId: string | undefined;
      let collectionFolio: string | undefined;
      if (allocated.length > 0) {
        const expectedAmount = allocated.reduce((sum, row) => sum + row.amount, 0);
        const folioResult = await createCollectionFolio({
          customer_id: customer.id,
          customer_name: customer.party_name,
          expected_amount: expectedAmount,
          documents: allocated.map(({ remision, amount: rowAmount }) => ({
            sales_document_id: remision.id,
            sales_folio: remision.folio,
            customer_id: remision.customer_id,
            customer_name: remision.customer_name_snapshot,
            document_total: Number(remision.total || 0),
            balance_total: balance(remision),
            amount_to_collect: rowAmount,
          })),
        });
        collectionFolioId = folioResult.collection_folio.id;
        collectionFolio = folioResult.collection_folio.folio;
      }

      const paymentResult = await createPayment({
        collection_folio_id: collectionFolioId,
        collection_folio: collectionFolio,
        customer_id: customer.id,
        customer_name: customer.party_name,
        payment_method: paymentMethod,
        amount: amountNumber,
        destination_money_account_id: accountId,
        bank_name: needsBankFields ? bankName.trim() : undefined,
        reference: reference.trim() || undefined,
        tracking_key: trackingKey.trim() || undefined,
        payment_date: paymentDate,
        notes: notes.trim() || undefined,
        ...receiptFields,
        metadata: {
          source_form: 'payment_capture',
          selected_remisiones: allocated.map(({ remision, amount: rowAmount }) => ({ id: remision.id, folio: remision.folio, amount_applied: rowAmount })),
        },
      });

      for (const row of allocated) {
        await applyPayment({ payment_id: paymentResult.payment.id, sales_document_id: row.remision.id, amount_applied: row.amount });
      }

      setNotice(`Pago ${paymentResult.payment.folio} registrado${allocated.length ? ' y aplicado' : ' sin aplicar'}.`);
      setAmount('');
      setSelectedRemisiones([]);
      setBankName('');
      setReference('');
      setTrackingKey('');
      setNotes('');
      setReceipt(null);
      if (customer) setRemisiones(await getRemisiones(customer.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el pago');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-slate-200 bg-white px-4 py-4 lg:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">{companyLabel} · {projectContext.project_label}</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-950">Captura de pagos</h1>
          </div>
          <button
            type="button"
            onClick={refreshBase}
            className="inline-flex h-10 items-center gap-2 rounded border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={16} />
            Actualizar
          </button>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-5 px-4 py-5 lg:grid-cols-[1fr_340px] lg:px-8">
        <div className="space-y-4">
          {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          {notice && <div className="rounded border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</div>}

          <section className="rounded border border-slate-200 bg-white p-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="lg:col-span-2">
                <label className="block">
                  <span className="text-xs font-medium text-slate-600">Cliente</span>
                  <div className="relative mt-1">
                    <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                    <input
                      value={customerSearch}
                      onChange={(event) => {
                        setCustomerSearch(event.target.value);
                        setCustomerOpen(true);
                        if (customer && event.target.value !== customer.party_name) setCustomer(null);
                      }}
                      onFocus={() => setCustomerOpen(true)}
                      placeholder="Buscar cliente"
                      className="h-10 w-full rounded border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-slate-500"
                    />
                  </div>
                </label>
                {customerOpen && !customer && (
                  <div className="mt-2 overflow-hidden rounded border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-100 px-3 py-2 text-xs text-slate-500">
                      {customers.length ? `${customers.length} clientes activos cargados` : loading ? 'Cargando clientes activos...' : 'No se cargaron clientes activos'}
                    </div>
                    {filteredCustomers.map((row) => (
                      <button
                        key={row.id}
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => selectCustomer(row)}
                        className="flex w-full items-center justify-between border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-slate-50"
                      >
                        <span className="font-medium text-slate-800">{row.party_name}</span>
                        <span className="text-xs text-slate-400">{row.folio || row.phone || ''}</span>
                      </button>
                    ))}
                    {customers.length > filteredCustomers.length && !customerSearch && <p className="px-3 py-2 text-xs text-slate-500">Escribe para buscar entre todos los clientes activos.</p>}
                    {!filteredCustomers.length && <p className="px-3 py-2 text-sm text-slate-500">Sin coincidencias</p>}
                  </div>
                )}
              </div>

              <Select label="Metodo de pago" value={paymentMethod} onChange={setPaymentMethod}>
                {paymentMethods.map((method) => (
                  <option key={method.value} value={method.value}>
                    {method.label}
                  </option>
                ))}
              </Select>
              <Input label="Importe" type="number" value={amount} onChange={setAmount} />
              <Select label="Cuenta destino" value={accountId} onChange={setAccountId}>
                <option value="">Selecciona cuenta</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.account_name} · {money(account.current_balance)}
                  </option>
                ))}
              </Select>
              <Input label="Fecha de pago" type="date" value={paymentDate} onChange={setPaymentDate} />

              {needsBankFields && (
                <>
                  <Input label="Banco" value={bankName} onChange={setBankName} />
                  <Input label="Referencia" value={reference} onChange={setReference} />
                  <Input label="Clave de rastreo" value={trackingKey} onChange={setTrackingKey} />
                </>
              )}

              <label className="block lg:col-span-2">
                <span className="text-xs font-medium text-slate-600">Comprobante</span>
                <div className="mt-1 flex items-center gap-3 rounded border border-dashed border-slate-300 bg-slate-50 px-3 py-3">
                  <FileUp className="text-slate-400" size={18} />
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,application/pdf"
                    onChange={(event) => setReceipt(event.target.files?.[0] ?? null)}
                    className="min-w-0 flex-1 text-sm text-slate-600"
                  />
                </div>
              </label>

              <label className="block lg:col-span-2">
                <span className="text-xs font-medium text-slate-600">Notas</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-500"
                />
              </label>
            </div>
          </section>

          <section className="rounded border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Remisiones con saldo</h2>
                <p className="mt-0.5 text-xs text-slate-500">{customer ? `${remisiones.length} disponibles para ${customer.party_name}` : 'Selecciona un cliente'}</p>
              </div>
              {loading && <Loader2 className="animate-spin text-slate-400" size={18} />}
            </div>
            <div className="divide-y divide-slate-100">
              {remisiones.map((remision) => {
                const selected = selectedRemisiones.includes(remision.id);
                return (
                  <label key={remision.id} className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-slate-50 ${selected ? 'bg-blue-50' : ''}`}>
                    <input type="checkbox" checked={selected} onChange={() => toggleRemision(remision.id)} className="h-4 w-4" />
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-sm font-semibold text-slate-900">{remision.folio}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{remision.document_date} · {remision.status}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-900">{money(balance(remision))}</p>
                      <p className="text-xs text-slate-500">saldo</p>
                    </div>
                  </label>
                );
              })}
              {customer && !remisiones.length && <p className="px-4 py-6 text-center text-sm text-slate-500">Sin remisiones pendientes para este cliente</p>}
            </div>
          </section>
        </div>

        <aside className="h-fit rounded border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2">
            <WalletCards className="text-slate-500" size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Resumen</h2>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            <SummaryRow label="Cliente" value={customer?.party_name || '-'} />
            <SummaryRow label="Importe" value={money(amountNumber)} />
            <SummaryRow label="Aplicado" value={money(selectedTotal)} />
            <SummaryRow label="Sin aplicar" value={money(unappliedPreview)} />
            <SummaryRow label="Comprobante" value={receipt ? receipt.name : '-'} />
          </div>
          <button
            type="button"
            disabled={saving || loading}
            onClick={submit}
            className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {saving ? <Loader2 className="animate-spin" size={17} /> : <Banknote size={17} />}
            Registrar pago
          </button>
          {notice && (
            <div className="mt-4 flex items-start gap-2 rounded bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              <CheckCircle2 className="mt-0.5" size={16} />
              <span>{notice}</span>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}

function Input({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <input
        value={value}
        type={type}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500"
      />
    </label>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
        {children}
      </select>
    </label>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 last:border-b-0">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-900">{value}</span>
    </div>
  );
}
