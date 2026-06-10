'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Ban,
  Banknote,
  Building2,
  CircleDollarSign,
  ClipboardCheck,
  FileText,
  Landmark,
  Plus,
  Printer,
  RefreshCw,
  Save,
  Search,
  Trash2,
  WalletCards,
} from 'lucide-react';
import {
  applyPayment,
  cancelCollectionFolio,
  createCollectionFolio,
  createMoneyAccount,
  createPayment,
  getCollectionFolioHtml,
  getDashboardData,
  getMoneyAccounts,
  getRemisiones,
  openHtml,
  type CollectionDocument,
  type CollectionFolio,
  type DashboardData,
  type MoneyAccount,
  type Payment,
  type PaymentApplication,
  type Remision,
} from '../lib/api';
import projectContext from '../project-context.json';

type Tab = 'cobranza' | 'folios' | 'cuentas' | 'corte';

const tabs: Array<{ id: Tab; label: string; icon: any }> = [
  { id: 'cobranza', label: 'Cobranza', icon: CircleDollarSign },
  { id: 'folios', label: 'Folios', icon: FileText },
  { id: 'cuentas', label: 'Cuentas', icon: Landmark },
  { id: 'corte', label: 'Corte de caja', icon: ClipboardCheck },
];

const emptyData: DashboardData = {
  kpis: {
    collected_today: 0,
    unapplied_total: 0,
    receivable_total: 0,
    active_accounts: 0,
    pending_folios: 0,
    pending_validation: 0,
  },
  payments: [],
  payment_applications: [],
  collection_folios: [],
  money_accounts: [],
  work_queue: { pending_folios: [], pending_validation: [] },
};

function mxn(value: number | string | null | undefined) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(value || 0));
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function pendingBalance(remision: Remision) {
  return Number(remision.balance_total ?? remision.total ?? 0);
}

function isActivePendingRemision(remision: Remision) {
  return String(remision.status || '').toLowerCase() !== 'cancelada' && pendingBalance(remision) > 0;
}

function customerKey(remision: Remision) {
  return String(remision.customer_id || remision.customer_name_snapshot || '').trim().toLowerCase();
}

function folioDocuments(folio: CollectionFolio): CollectionDocument[] {
  const docs = folio.metadata?.documents;
  if (Array.isArray(docs) && docs.length) return docs;
  return [
    {
      sales_document_id: undefined,
      sales_folio: folio.sales_folio,
      customer_name: folio.customer_name,
      document_total: folio.expected_amount,
      balance_total: folio.balance_amount,
      amount_to_collect: folio.expected_amount,
    },
  ];
}

function sumDocs(folio: CollectionFolio, key: keyof CollectionDocument, fallback: number) {
  const docs = folioDocuments(folio);
  const total = docs.reduce((sum, doc) => sum + Number(doc[key] || 0), 0);
  return total || fallback;
}

function savedTab(): Tab {
  if (typeof window === 'undefined') return 'cobranza';
  const value = window.localStorage.getItem('duralon_billing_tab');
  return tabs.some((tab) => tab.id === value) ? (value as Tab) : 'cobranza';
}

export default function BillingDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('cobranza');
  const [data, setData] = useState<DashboardData>(emptyData);
  const [accounts, setAccounts] = useState<MoneyAccount[]>([]);
  const [remisiones, setRemisiones] = useState<Remision[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const [dashboard, accountRows, remisionRows] = await Promise.all([getDashboardData(), getMoneyAccounts(), getRemisiones()]);
      setData({ ...emptyData, ...dashboard, payment_applications: dashboard.payment_applications ?? [] });
      setAccounts(accountRows);
      setRemisiones(remisionRows);
    } catch (err: any) {
      setError(err.message || 'No se pudo cargar billing');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setActiveTab(savedTab());
    refresh();
  }, []);

  useEffect(() => {
    window.localStorage.setItem('duralon_billing_tab', activeTab);
  }, [activeTab]);

  const filteredFolios = useMemo(() => filterRows(data.collection_folios, search, ['folio', 'sales_folio', 'customer_name', 'status']), [data.collection_folios, search]);
  const filteredPayments = useMemo(() => filterRows(data.payments, search, ['folio', 'collection_folio', 'customer_name', 'payment_method', 'status']), [data.payments, search]);

  async function runAction(fn: () => Promise<void>, okMessage: string) {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await fn();
      setNotice(okMessage);
      await refresh();
    } catch (err: any) {
      setError(err.message || 'No se pudo guardar');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4f6f8]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white px-5 py-6 lg:block">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-slate-900 text-white">
            <Building2 size={20} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">{projectContext.company_label}</p>
            <h1 className="text-lg font-semibold text-slate-950">Billing</h1>
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
          <p className="mt-1 text-xs text-slate-500">{projectContext.schema_label}</p>
        </div>
      </aside>

      <section className="lg:ml-64">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-4 py-4 backdrop-blur lg:px-8">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">{projectContext.project_label} - Cobranza operativa</p>
              <h2 className="text-2xl font-semibold text-slate-950">Duralon Billing</h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar folio, cliente o pago"
                  className="h-10 w-64 rounded border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-slate-500"
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
                onClick={() => setActiveTab(tab.id)}
                className={`whitespace-nowrap rounded px-3 py-2 text-sm font-medium ${activeTab === tab.id ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}
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
          {activeTab === 'cobranza' && (
            <CobranzaPanel
              payments={filteredPayments}
              applications={data.payment_applications}
              folios={data.collection_folios}
              remisiones={remisiones}
              accounts={accounts}
              saving={saving}
              runAction={runAction}
            />
          )}
          {activeTab === 'folios' && <FoliosPanel folios={filteredFolios} remisiones={remisiones} saving={saving} runAction={runAction} />}
          {activeTab === 'cuentas' && <CuentasPanel accounts={accounts} saving={saving} runAction={runAction} />}
          {activeTab === 'corte' && <CortePanel accounts={accounts} saving={saving} runAction={runAction} />}
        </div>
      </section>
    </main>
  );
}

function Kpis({ data, loading }: { data: DashboardData; loading: boolean }) {
  const rows = [
    { label: 'Cobrado hoy', value: mxn(data.kpis.collected_today), icon: Banknote },
    { label: 'Por aplicar', value: mxn(data.kpis.unapplied_total), icon: WalletCards },
    { label: 'Saldo folios', value: mxn(data.kpis.receivable_total), icon: FileText },
    { label: 'Cuentas activas', value: String(data.kpis.active_accounts), icon: Landmark },
  ];
  return (
    <div className="mb-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {rows.map((row) => {
        const Icon = row.icon;
        return (
          <div key={row.label} className="rounded border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-500">{row.label}</p>
              <Icon className="text-slate-400" size={18} />
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-950">{loading ? '-' : row.value}</p>
          </div>
        );
      })}
    </div>
  );
}

function CobranzaPanel({
  payments,
  applications,
  folios,
  remisiones,
  accounts,
  saving,
  runAction,
}: {
  payments: Payment[];
  applications: PaymentApplication[];
  folios: CollectionFolio[];
  remisiones: Remision[];
  accounts: MoneyAccount[];
  saving: boolean;
  runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void>;
}) {
  const [selectedFolioRows, setSelectedFolioRows] = useState<Array<{ folioId: string }>>([{ folioId: '' }]);
  const [method, setMethod] = useState('cash');
  const [amount, setAmount] = useState('');
  const [accountId, setAccountId] = useState('');
  const [paymentId, setPaymentId] = useState('');
  const [remisionId, setRemisionId] = useState('');
  const [applyAmount, setApplyAmount] = useState('');
  const pendingRemisiones = useMemo(() => remisiones.filter(isActivePendingRemision), [remisiones]);
  const activeFolios = useMemo(
    () => folios.filter((folio) => !['cancelado', 'cancelada', 'pagada'].includes(String(folio.status || '').toLowerCase()) && Number(folio.balance_amount || 0) > 0),
    [folios]
  );
  const selectedFolios = selectedFolioRows
    .map((row) => activeFolios.find((folio) => folio.id === row.folioId))
    .filter((folio): folio is CollectionFolio => Boolean(folio));
  const firstFolio = selectedFolios[0];
  const selectedCustomer = firstFolio ? String(firstFolio.customer_name || '').trim().toLowerCase() : '';
  const folioTotal = selectedFolios.reduce((sum, folio) => sum + Number(folio.balance_amount || 0), 0);
  const unappliedPayments = useMemo(() => payments.filter((payment) => Number(payment.unapplied_amount ?? payment.amount ?? 0) > 0 && payment.status !== 'cancelado'), [payments]);

  function folioOptionsForRow(index: number) {
    const used = new Set(selectedFolioRows.map((row, rowIndex) => (rowIndex === index ? '' : row.folioId)).filter(Boolean));
    const rowId = selectedFolioRows[index]?.folioId;
    return activeFolios.filter((folio) => {
      if (used.has(folio.id)) return false;
      if (!selectedCustomer) return true;
      return String(folio.customer_name || '').trim().toLowerCase() === selectedCustomer || folio.id === rowId;
    });
  }

  const extraFolioOptions = selectedCustomer
    ? activeFolios.filter((folio) => String(folio.customer_name || '').trim().toLowerCase() === selectedCustomer && !selectedFolioRows.some((row) => row.folioId === folio.id))
    : [];

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <div className="space-y-4">
        <section className="rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Registrar pago</h3>
          <div className="mt-4 space-y-3">
            {selectedFolioRows.map((row, index) => {
              const selected = activeFolios.find((folio) => folio.id === row.folioId);
              return (
                <div key={`${index}-${row.folioId || 'empty'}`} className="rounded border border-slate-200 bg-slate-50 p-2">
                  <Select
                    label={index === 0 ? 'Folio de cobranza' : 'Otro folio'}
                    value={row.folioId}
                    onChange={(value) =>
                      setSelectedFolioRows((current) => {
                        const next = [...current];
                        next[index] = { folioId: value };
                        return index === 0 && value ? [next[0]] : next;
                      })
                    }
                  >
                    <option value="">Sin folio / pago directo</option>
                    {folioOptionsForRow(index).map((folio) => (
                      <option key={folio.id} value={folio.id}>
                        {folio.folio} - {folio.customer_name || 'Cliente'} - {mxn(folio.balance_amount)}
                      </option>
                    ))}
                  </Select>
                  {selected && <p className="mt-1 text-xs text-slate-500">Saldo de referencia: {mxn(selected.balance_amount)}</p>}
                </div>
              );
            })}
            {extraFolioOptions.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedFolioRows((current) => [...current, { folioId: '' }])}
                className="flex h-9 w-full items-center justify-center gap-2 rounded border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Plus size={15} />
                Agregar otro folio
              </button>
            )}
            {selectedFolios.length > 0 && <div className="rounded bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">Total folios: {mxn(folioTotal)}</div>}
            <div className="grid grid-cols-2 gap-3">
              <Select label="Metodo" value={method} onChange={setMethod}>
                <option value="cash">Efectivo</option>
                <option value="transfer">Transferencia</option>
                <option value="deposit">Deposito</option>
                <option value="card">Tarjeta</option>
                <option value="check">Cheque</option>
                <option value="other">Otro</option>
              </Select>
              <Input label="Importe" type="number" value={amount} onChange={setAmount} />
            </div>
            <Select label="Cuenta destino" value={accountId} onChange={setAccountId}>
              <option value="">Sin cuenta</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.account_name}
                </option>
              ))}
            </Select>
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                runAction(async () => {
                  if (selectedFolios.length > 1) {
                    const customer = String(selectedFolios[0]?.customer_name || '').trim().toLowerCase();
                    if (selectedFolios.some((folio) => String(folio.customer_name || '').trim().toLowerCase() !== customer)) {
                      throw new Error('Todos los folios del pago deben ser del mismo cliente');
                    }
                  }
                  await createPayment({
                    collection_folio_id: selectedFolios[0]?.id,
                    collection_folios: selectedFolios.map((folio) => ({
                      id: folio.id,
                      folio: folio.folio,
                      customer_name: folio.customer_name,
                      expected_amount: folio.expected_amount,
                      balance_amount: folio.balance_amount,
                    })),
                    payment_method: method,
                    amount: Number(amount || 0),
                    destination_money_account_id: accountId || undefined,
                    customer_name: selectedFolios[0]?.customer_name || undefined,
                  });
                  setAmount('');
                  setSelectedFolioRows([{ folioId: '' }]);
                }, 'Pago registrado')
              }
              className="flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
            >
              <Save size={16} />
              Guardar pago
            </button>
          </div>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Aplicar pago a remision</h3>
          <div className="mt-4 space-y-3">
            <Select label="Pago" value={paymentId} onChange={setPaymentId}>
              <option value="">Selecciona pago</option>
              {unappliedPayments.map((payment) => (
                <option key={payment.id} value={payment.id}>
                  {payment.folio} - {mxn(payment.unapplied_amount || payment.amount)}
                </option>
              ))}
            </Select>
            <Select label="Remision" value={remisionId} onChange={setRemisionId}>
              <option value="">Selecciona remision</option>
              {pendingRemisiones.map((remision) => (
                <option key={remision.id} value={remision.id}>
                  {remision.folio} - {remision.customer_name_snapshot} - {mxn(remision.balance_total ?? remision.total)}
                </option>
              ))}
            </Select>
            <Input label="Importe a aplicar" type="number" value={applyAmount} onChange={setApplyAmount} />
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                runAction(async () => {
                  await applyPayment({ payment_id: paymentId, sales_document_id: remisionId, amount_applied: Number(applyAmount || 0) });
                  setApplyAmount('');
                }, 'Pago aplicado')
              }
              className="flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
            >
              <Save size={16} />
              Aplicar pago
            </button>
          </div>
        </section>
      </div>
      <PaymentsLedger payments={payments} applications={applications} />
    </div>
  );
}

function FoliosPanel({
  folios,
  remisiones,
  saving,
  runAction,
}: {
  folios: CollectionFolio[];
  remisiones: Remision[];
  saving: boolean;
  runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void>;
}) {
  const [selectedDocs, setSelectedDocs] = useState<Array<{ remisionId: string; amount: string }>>([{ remisionId: '', amount: '' }]);
  const [collector, setCollector] = useState('');

  const pendingRemisiones = useMemo(() => remisiones.filter(isActivePendingRemision), [remisiones]);
  const firstSelected = pendingRemisiones.find((item) => item.id === selectedDocs[0]?.remisionId);
  const activeCustomer = firstSelected ? customerKey(firstSelected) : '';
  const collectorOptions = useMemo(
    () => Array.from(new Set(folios.map((folio) => folio.collector_name).filter(Boolean) as string[])).sort((a, b) => a.localeCompare(b)),
    [folios]
  );
  const selectedRemisiones = selectedDocs
    .map((doc) => ({ item: pendingRemisiones.find((remision) => remision.id === doc.remisionId), amount: doc.amount }))
    .filter((doc): doc is { item: Remision; amount: string } => Boolean(doc.item));
  const totalToCollect = selectedRemisiones.reduce((sum, doc) => sum + Number(doc.amount || 0), 0);

  function updateSelectedDoc(index: number, patch: Partial<{ remisionId: string; amount: string }>) {
    setSelectedDocs((current) => {
      const next = [...current];
      const currentRow = next[index] ?? { remisionId: '', amount: '' };
      const remision = patch.remisionId ? pendingRemisiones.find((item) => item.id === patch.remisionId) : undefined;
      next[index] = {
        ...currentRow,
        ...patch,
        amount: patch.remisionId && remision ? String(pendingBalance(remision)) : patch.amount ?? currentRow.amount,
      };
      return index === 0 && patch.remisionId ? [next[0]] : next;
    });
  }

  function optionsForRow(index: number) {
    const used = new Set(selectedDocs.map((doc, docIndex) => (docIndex === index ? '' : doc.remisionId)).filter(Boolean));
    const rowId = selectedDocs[index]?.remisionId;
    return pendingRemisiones.filter((remision) => {
      if (used.has(remision.id)) return false;
      if (!activeCustomer) return true;
      return customerKey(remision) === activeCustomer || rowId === remision.id;
    });
  }

  const extraOptions = activeCustomer
    ? pendingRemisiones.filter((remision) => customerKey(remision) === activeCustomer && !selectedDocs.some((doc) => doc.remisionId === remision.id))
    : [];

  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <section className="rounded border border-slate-200 bg-white p-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Crear folio de cobranza</h3>
        <div className="mt-3 space-y-3">
          {selectedDocs.map((doc, index) => {
            const selected = pendingRemisiones.find((item) => item.id === doc.remisionId);
            return (
              <div key={`${index}-${doc.remisionId || 'empty'}`} className="rounded border border-slate-200 bg-slate-50 p-2">
                <Select label={index === 0 ? 'Remision' : 'Otra remision'} value={doc.remisionId} onChange={(value) => updateSelectedDoc(index, { remisionId: value })}>
                  <option value="">Selecciona remision</option>
                  {optionsForRow(index).map((remision) => (
                    <option key={remision.id} value={remision.id}>
                      {remision.folio} - {remision.customer_name_snapshot} - saldo {mxn(pendingBalance(remision))}
                    </option>
                  ))}
                </Select>
                <div className="mt-2 grid grid-cols-[1fr_auto] gap-2">
                  <Input label="X cobrar" type="number" value={doc.amount} onChange={(value) => updateSelectedDoc(index, { amount: value })} />
                  <button
                    type="button"
                    disabled={selectedDocs.length === 1}
                    onClick={() => setSelectedDocs((current) => current.filter((_, docIndex) => docIndex !== index))}
                    className="mt-5 flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                    title="Quitar remision"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                {selected && <p className="mt-1 text-xs text-slate-500">Saldo pendiente: {mxn(pendingBalance(selected))}</p>}
              </div>
            );
          })}
          {extraOptions.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedDocs((current) => [...current, { remisionId: '', amount: '' }])}
              className="flex h-9 w-full items-center justify-center gap-2 rounded border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <Plus size={15} />
              Agregar otra remision
            </button>
          )}
          <Input label="Cobrador" value={collector} onChange={setCollector} list="collector-options" />
          <datalist id="collector-options">
            {collectorOptions.map((name) => (
              <option key={name} value={name} />
            ))}
          </datalist>
          <div className="rounded bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">Total del folio: {mxn(totalToCollect)}</div>
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              runAction(async () => {
                if (!selectedRemisiones.length) throw new Error('Selecciona al menos una remision');
                if (selectedRemisiones.some((doc) => Number(doc.amount || 0) <= 0)) throw new Error('Cada importe por cobrar debe ser mayor a 0');
                const documents = selectedRemisiones.map(({ item, amount }) => ({
                  sales_document_id: item.id,
                  sales_folio: item.folio,
                  customer_id: item.customer_id,
                  customer_name: item.customer_name_snapshot,
                  document_total: Number(item.total || 0),
                  balance_total: pendingBalance(item),
                  amount_to_collect: Number(amount || 0),
                }));
                await createCollectionFolio({
                  sales_document_id: selectedRemisiones[0]?.item.id,
                  sales_folio: selectedRemisiones[0]?.item.folio,
                  customer_name: selectedRemisiones[0]?.item.customer_name_snapshot,
                  expected_amount: totalToCollect,
                  collector_name: collector || undefined,
                  documents,
                });
                setSelectedDocs([{ remisionId: '', amount: '' }]);
              }, 'Folio creado')
            }
            className="flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            <Save size={16} />
            Crear folio
          </button>
        </div>
      </section>
      <FoliosTable folios={folios} runAction={runAction} saving={saving} />
    </div>
  );
}

function CuentasPanel({
  accounts,
  saving,
  runAction,
}: {
  accounts: MoneyAccount[];
  saving: boolean;
  runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void>;
}) {
  const [type, setType] = useState('cash_box');
  const [name, setName] = useState('');
  const [bank, setBank] = useState('');
  const [responsible, setResponsible] = useState('');

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Nueva cuenta de dinero</h3>
        <div className="mt-4 space-y-3">
          <Select label="Tipo" value={type} onChange={setType}>
            <option value="bank">Banco</option>
            <option value="cash">Efectivo</option>
            <option value="cash_box">Caja</option>
            <option value="collector_cash">Caja cobrador</option>
            <option value="card_terminal">Terminal</option>
            <option value="other">Otro</option>
          </Select>
          <Input label="Nombre de cuenta" value={name} onChange={setName} />
          <Input label="Banco" value={bank} onChange={setBank} />
          <Input label="Responsable" value={responsible} onChange={setResponsible} />
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              runAction(async () => {
                await createMoneyAccount({ account_type: type, account_name: name, bank_name: bank || undefined, responsible_user: responsible || undefined });
                setName('');
                setBank('');
                setResponsible('');
              }, 'Cuenta creada')
            }
            className="flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            <Save size={16} />
            Crear cuenta
          </button>
        </div>
      </section>
      <AccountsTable accounts={accounts} />
    </div>
  );
}

function CortePanel({ accounts }: { accounts: MoneyAccount[]; saving: boolean; runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void> }) {
  return (
    <section className="rounded border border-slate-200 bg-white p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Corte de caja</h3>
      <p className="mt-3 max-w-2xl text-sm text-slate-600">
        El backend ya tiene skills para abrir y cerrar cortes. La UI completa de corte queda como siguiente paso: seleccionar cobrador, cuenta destino,
        importe esperado, conteo y diferencia.
      </p>
      <div className="mt-4 overflow-hidden rounded border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr><th className="px-3 py-2">Cuenta</th><th className="px-3 py-2">Tipo</th><th className="px-3 py-2 text-right">Saldo</th></tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium">{account.account_name}</td>
                <td className="px-3 py-2 text-slate-500">{account.account_type}</td>
                <td className="px-3 py-2 text-right">{mxn(account.current_balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function paymentFolios(payment: Payment) {
  const rows = payment.metadata?.collection_folios;
  if (Array.isArray(rows) && rows.length) return rows.map((row) => row.folio).filter(Boolean).join(', ');
  return payment.collection_folio || '-';
}

function PaymentsLedger({ payments, applications }: { payments: Payment[]; applications: PaymentApplication[] }) {
  const pending = payments.filter((payment) => Number(payment.unapplied_amount ?? payment.amount ?? 0) > 0 && payment.status !== 'cancelado');
  const appliedPaymentIds = new Set(applications.map((application) => application.payment_id));
  const applied = payments.filter((payment) => appliedPaymentIds.has(payment.id) || Number(payment.unapplied_amount || 0) <= 0);

  return (
    <div className="space-y-5">
      <section className="rounded border border-red-200 bg-white">
        <TableHeader title="Pagos sin aplicar" count={pending.length} tone="red" />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-red-50 text-xs uppercase text-red-700">
              <tr>
                <th className="px-3 py-2">Pago</th>
                <th className="px-3 py-2">Folios</th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2 text-right">Importe</th>
                <th className="px-3 py-2 text-right">Sin aplicar</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {pending.map((payment) => (
                <tr key={payment.id} className="border-t border-red-100">
                  <td className="px-3 py-2 font-mono font-medium">{payment.folio}</td>
                  <td className="px-3 py-2">{paymentFolios(payment)}</td>
                  <td className="px-3 py-2">{payment.customer_name || '-'}</td>
                  <td className="px-3 py-2 text-right">{mxn(payment.amount)}</td>
                  <td className="px-3 py-2 text-right font-semibold text-red-700">{mxn(payment.unapplied_amount ?? payment.amount)}</td>
                  <td className="px-3 py-2"><Badge value="sin_aplicar" /></td>
                </tr>
              ))}
              {!pending.length && <EmptyRow cols={6} label="No hay pagos pendientes de aplicar" />}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded border border-slate-200 bg-white">
        <TableHeader title="Pagos aplicados" count={applied.length} />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Pago</th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">Remisiones aplicadas</th>
                <th className="px-3 py-2 text-right">Aplicado</th>
                <th className="px-3 py-2 text-right">Saldo remision</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {applied.map((payment) => {
                const rows = applications.filter((application) => application.payment_id === payment.id);
                const remisiones = rows.map((row) => row.sales_folio).filter(Boolean).join(', ') || '-';
                const appliedAmount = rows.reduce((sum, row) => sum + Number(row.amount_applied || 0), 0);
                const balanceAfter = rows.length ? rows[rows.length - 1]?.metadata?.document_balance_after : undefined;
                return (
                  <tr key={payment.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono font-medium">{payment.folio}</td>
                    <td className="px-3 py-2">{payment.customer_name || '-'}</td>
                    <td className="px-3 py-2">{remisiones}</td>
                    <td className="px-3 py-2 text-right">{mxn(appliedAmount || payment.amount - Number(payment.unapplied_amount || 0))}</td>
                    <td className="px-3 py-2 text-right">{balanceAfter === undefined ? '-' : mxn(balanceAfter)}</td>
                    <td className="px-3 py-2"><Badge value={payment.status} /></td>
                  </tr>
                );
              })}
              {!applied.length && <EmptyRow cols={6} label="Todavia no hay pagos aplicados" />}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function FoliosTable({
  folios,
  runAction,
  saving,
}: {
  folios: CollectionFolio[];
  runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void>;
  saving: boolean;
}) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <TableHeader title="Folios de cobranza" count={folios.length} />
      <div className="space-y-3 p-3 md:hidden">
        {folios.map((folio) => {
          const docs = folioDocuments(folio);
          const status = String(folio.status || '').toLowerCase();
          return (
            <div key={folio.id} className="rounded border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-mono text-sm font-semibold text-slate-950">{folio.folio}</p>
                  <p className="text-xs text-slate-500">{folio.customer_name || '-'}</p>
                </div>
                <Badge value={folio.status} />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                <Metric label="Remision" value={docs.map((doc) => doc.sales_folio).filter(Boolean).join(', ') || '-'} />
                <Metric label="Saldo" value={mxn(sumDocs(folio, 'balance_total', folio.balance_amount))} />
                <Metric label="X cobrar" value={mxn(sumDocs(folio, 'amount_to_collect', folio.expected_amount))} />
              </div>
              <div className="mt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={async () => openHtml(await getCollectionFolioHtml(folio.folio))}
                  className="inline-flex h-8 items-center gap-1 rounded border border-slate-200 px-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Printer size={14} />
                  PDF
                </button>
                <button
                  type="button"
                  disabled={saving || status === 'cancelado' || Boolean(folio.payment_id)}
                  onClick={() =>
                    runAction(async () => {
                      await cancelCollectionFolio({ collection_folio_id: folio.id, cancel_reason: 'cancelado desde dashboard' });
                    }, 'Folio cancelado')
                  }
                  className="inline-flex h-8 w-8 items-center justify-center rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-30"
                  title="Cancelar folio"
                >
                  <Ban size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-2 py-2">Folio</th>
              <th className="px-2 py-2">Cliente</th>
              <th className="px-2 py-2">Remisiones</th>
              <th className="px-2 py-2 text-right">Importe</th>
              <th className="px-2 py-2 text-right">Saldo</th>
              <th className="px-2 py-2 text-right">X cobrar</th>
              <th className="px-2 py-2">Status</th>
              <th className="px-2 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {folios.map((folio) => {
              const docs = folioDocuments(folio);
              const status = String(folio.status || '').toLowerCase();
              return (
                <tr key={folio.id} className="border-t border-slate-100">
                  <td className="px-2 py-2 font-mono font-medium">{folio.folio}</td>
                  <td className="px-2 py-2">{folio.customer_name || '-'}</td>
                  <td className="px-2 py-2">{docs.map((doc) => doc.sales_folio).filter(Boolean).join(', ') || '-'}</td>
                  <td className="px-2 py-2 text-right">{mxn(sumDocs(folio, 'document_total', folio.expected_amount))}</td>
                  <td className="px-2 py-2 text-right">{mxn(sumDocs(folio, 'balance_total', folio.balance_amount))}</td>
                  <td className="px-2 py-2 text-right">{mxn(sumDocs(folio, 'amount_to_collect', folio.expected_amount))}</td>
                  <td className="px-2 py-2"><Badge value={folio.status} /></td>
                  <td className="px-2 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={async () => openHtml(await getCollectionFolioHtml(folio.folio))}
                        className="inline-flex h-8 items-center gap-1 rounded border border-slate-200 px-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <Printer size={14} />
                        PDF
                      </button>
                      <button
                        type="button"
                        disabled={saving || status === 'cancelado' || Boolean(folio.payment_id)}
                        onClick={() =>
                          runAction(async () => {
                            await cancelCollectionFolio({ collection_folio_id: folio.id, cancel_reason: 'cancelado desde dashboard' });
                          }, 'Folio cancelado')
                        }
                        className="inline-flex h-8 w-8 items-center justify-center rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-30"
                        title="Cancelar folio"
                      >
                        <Ban size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AccountsTable({ accounts }: { accounts: MoneyAccount[] }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <TableHeader title="Cuentas de dinero" count={accounts.length} />
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr><th className="px-3 py-2">Cuenta</th><th className="px-3 py-2">Tipo</th><th className="px-3 py-2">Responsable</th><th className="px-3 py-2 text-right">Saldo</th><th className="px-3 py-2">Status</th></tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium">{account.account_name}</td>
                <td className="px-3 py-2 text-slate-500">{account.account_type}</td>
                <td className="px-3 py-2">{account.responsible_user || '-'}</td>
                <td className="px-3 py-2 text-right">{mxn(account.current_balance)}</td>
                <td className="px-3 py-2"><Badge value={account.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TableHeader({ title, count, tone = 'slate' }: { title: string; count: number; tone?: 'slate' | 'red' }) {
  const badgeClass = tone === 'red' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600';
  return (
    <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{title}</h3>
      <span className={`rounded px-2 py-1 text-xs font-medium ${badgeClass}`}>{count}</span>
    </div>
  );
}

function EmptyRow({ cols, label }: { cols: number; label: string }) {
  return (
    <tr>
      <td colSpan={cols} className="px-3 py-6 text-center text-sm text-slate-500">
        {label}
      </td>
    </tr>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded bg-slate-50 p-2">
      <p className="text-[10px] font-semibold uppercase text-slate-500">{label}</p>
      <p className="truncate text-xs font-medium text-slate-800">{value}</p>
    </div>
  );
}

function Badge({ value }: { value: string }) {
  const normalized = String(value || '').toLowerCase();
  const cls = normalized === 'sin_aplicar' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700';
  return <span className={`rounded px-2 py-1 text-xs font-medium ${cls}`}>{value || '-'}</span>;
}

function Input({
  label,
  value,
  onChange,
  type = 'text',
  list,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  list?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <input
        value={value}
        type={type}
        list={list}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-9 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500"
      />
    </label>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-9 w-full rounded border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500">
        {children}
      </select>
    </label>
  );
}

function filterRows<T extends Record<string, any>>(rows: T[], term: string, keys: string[]) {
  const clean = term.trim().toLowerCase();
  if (!clean) return rows;
  return rows.filter((row) => keys.some((key) => String(row[key] ?? '').toLowerCase().includes(clean)));
}
