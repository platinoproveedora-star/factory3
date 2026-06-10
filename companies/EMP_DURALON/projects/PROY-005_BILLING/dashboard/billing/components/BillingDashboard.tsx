'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Banknote,
  Building2,
  CircleDollarSign,
  ClipboardCheck,
  FileText,
  Landmark,
  Printer,
  RefreshCw,
  Save,
  Search,
  WalletCards,
} from 'lucide-react';
import {
  applyPayment,
  createCollectionFolio,
  createMoneyAccount,
  createPayment,
  getCollectionFolioHtml,
  getDashboardData,
  getMoneyAccounts,
  getRemisiones,
  openHtml,
  type CollectionFolio,
  type DashboardData,
  type MoneyAccount,
  type Payment,
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
      setData(dashboard);
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
  folios,
  remisiones,
  accounts,
  saving,
  runAction,
}: {
  payments: Payment[];
  folios: CollectionFolio[];
  remisiones: Remision[];
  accounts: MoneyAccount[];
  saving: boolean;
  runAction: (fn: () => Promise<void>, okMessage: string) => Promise<void>;
}) {
  const [collectionId, setCollectionId] = useState('');
  const [method, setMethod] = useState('cash');
  const [amount, setAmount] = useState('');
  const [accountId, setAccountId] = useState('');
  const [paymentId, setPaymentId] = useState('');
  const [remisionId, setRemisionId] = useState('');
  const [applyAmount, setApplyAmount] = useState('');

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <div className="space-y-4">
        <section className="rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Registrar pago</h3>
          <div className="mt-4 space-y-3">
            <Select label="Folio de cobranza" value={collectionId} onChange={setCollectionId}>
              <option value="">Sin folio / pago directo</option>
              {folios.map((folio) => (
                <option key={folio.id} value={folio.id}>
                  {folio.folio} - {folio.customer_name || 'Cliente'} - {mxn(folio.balance_amount)}
                </option>
              ))}
            </Select>
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
                  const folio = folios.find((item) => item.id === collectionId);
                  await createPayment({
                    collection_folio_id: collectionId || undefined,
                    payment_method: method,
                    amount: Number(amount || 0),
                    destination_money_account_id: accountId || undefined,
                    customer_name: folio?.customer_name || undefined,
                  });
                  setAmount('');
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
              {payments.map((payment) => (
                <option key={payment.id} value={payment.id}>
                  {payment.folio} - {mxn(payment.unapplied_amount || payment.amount)}
                </option>
              ))}
            </Select>
            <Select label="Remision" value={remisionId} onChange={setRemisionId}>
              <option value="">Selecciona remision</option>
              {remisiones.map((remision) => (
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
      <PaymentsTable payments={payments} />
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
  const [remisionId, setRemisionId] = useState('');
  const [amount, setAmount] = useState('');
  const [collector, setCollector] = useState('');

  const selected = remisiones.find((item) => item.id === remisionId);

  useEffect(() => {
    if (selected) setAmount(String(selected.balance_total ?? selected.total ?? ''));
  }, [selected]);

  return (
    <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Crear folio de cobranza</h3>
        <div className="mt-4 space-y-3">
          <Select label="Remision" value={remisionId} onChange={setRemisionId}>
            <option value="">Selecciona remision</option>
            {remisiones.map((remision) => (
              <option key={remision.id} value={remision.id}>
                {remision.folio} - {remision.customer_name_snapshot}
              </option>
            ))}
          </Select>
          <Input label="Importe esperado" type="number" value={amount} onChange={setAmount} />
          <Input label="Cobrador" value={collector} onChange={setCollector} />
          <button
            type="button"
            disabled={saving}
            onClick={() =>
              runAction(async () => {
                await createCollectionFolio({
                  sales_document_id: selected?.id,
                  sales_folio: selected?.folio,
                  customer_name: selected?.customer_name_snapshot,
                  expected_amount: Number(amount || 0),
                  collector_name: collector || undefined,
                });
              }, 'Folio creado')
            }
            className="flex h-10 w-full items-center justify-center gap-2 rounded bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            <Save size={16} />
            Crear folio
          </button>
        </div>
      </section>
      <FoliosTable folios={folios} />
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

function PaymentsTable({ payments }: { payments: Payment[] }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <TableHeader title="Pagos recientes" count={payments.length} />
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr><th className="px-3 py-2">Folio</th><th className="px-3 py-2">Cliente</th><th className="px-3 py-2">Metodo</th><th className="px-3 py-2 text-right">Importe</th><th className="px-3 py-2">Status</th></tr>
          </thead>
          <tbody>
            {payments.map((payment) => (
              <tr key={payment.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono font-medium">{payment.folio}</td>
                <td className="px-3 py-2">{payment.customer_name || '-'}</td>
                <td className="px-3 py-2 text-slate-500">{payment.payment_method}</td>
                <td className="px-3 py-2 text-right">{mxn(payment.amount)}</td>
                <td className="px-3 py-2"><Badge value={payment.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FoliosTable({ folios }: { folios: CollectionFolio[] }) {
  return (
    <section className="rounded border border-slate-200 bg-white">
      <TableHeader title="Folios de cobranza" count={folios.length} />
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr><th className="px-3 py-2">Folio</th><th className="px-3 py-2">Documento</th><th className="px-3 py-2">Cliente</th><th className="px-3 py-2 text-right">Saldo</th><th className="px-3 py-2">Status</th><th className="px-3 py-2"></th></tr>
          </thead>
          <tbody>
            {folios.map((folio) => (
              <tr key={folio.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono font-medium">{folio.folio}</td>
                <td className="px-3 py-2">{folio.sales_folio || '-'}</td>
                <td className="px-3 py-2">{folio.customer_name || '-'}</td>
                <td className="px-3 py-2 text-right">{mxn(folio.balance_amount)}</td>
                <td className="px-3 py-2"><Badge value={folio.status} /></td>
                <td className="px-3 py-2 text-right">
                  <button
                    type="button"
                    onClick={async () => openHtml(await getCollectionFolioHtml(folio.folio))}
                    className="inline-flex h-8 items-center gap-1 rounded border border-slate-200 px-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <Printer size={14} />
                    PDF
                  </button>
                </td>
              </tr>
            ))}
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

function TableHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{title}</h3>
      <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">{count}</span>
    </div>
  );
}

function Badge({ value }: { value: string }) {
  return <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">{value || '-'}</span>;
}

function Input({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <input value={value} type={type} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded border border-slate-200 px-3 text-sm outline-none focus:border-slate-500" />
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

function filterRows<T extends Record<string, any>>(rows: T[], term: string, keys: string[]) {
  const clean = term.trim().toLowerCase();
  if (!clean) return rows;
  return rows.filter((row) => keys.some((key) => String(row[key] ?? '').toLowerCase().includes(clean)));
}
