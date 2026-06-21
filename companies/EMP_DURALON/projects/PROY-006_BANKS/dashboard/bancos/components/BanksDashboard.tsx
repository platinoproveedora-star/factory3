'use client';

import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BadgeCheck,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  Download,
  FileText,
  KeyRound,
  Landmark,
  Loader2,
  LogOut,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
  XCircle
} from 'lucide-react';
import {
  banksApi,
  clearKey,
  getStoredKey,
  login,
  money,
  today,
  type Account,
  type Authorization,
  type DashboardData,
  type ExpenseReconciliationData,
  type ExpenseReconciliationRow,
  type Movement,
  type StatementExtraction,
  type StatementLine
} from '../lib/api';
import projectContext from '../project-context.json';

type Tab = 'resumen' | 'cuentas' | 'movimientos' | 'autorizaciones' | 'conciliacion' | 'conciliacion_gastos' | 'converter';

const emptyData: DashboardData = {
  accounts: [],
  movements: [],
  authorizations: [],
  kpis: {
    total_balance: 0,
    active_accounts: 0,
    pending_authorizations: 0,
    pending_reconciliation: 0,
    month_in: 0,
    month_out: 0
  }
};

const tabs: Array<{ id: Tab; label: string }> = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'cuentas', label: 'Cuentas' },
  { id: 'movimientos', label: 'Movimientos' },
  { id: 'autorizaciones', label: 'Autorizacion' },
  { id: 'conciliacion', label: 'Conciliacion' },
  { id: 'conciliacion_gastos', label: 'Conciliacion gastos' },
  { id: 'converter', label: 'Converter' }
];

function statusClass(status: string) {
  if (['active', 'autorizado', 'aprobado', 'conciliado', 'no_requerida'].includes(status)) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (['pendiente'].includes(status)) return 'bg-amber-50 text-amber-800 border-amber-200';
  if (['rechazado', 'closed', 'en_disputa'].includes(status)) return 'bg-rose-50 text-rose-700 border-rose-200';
  return 'bg-slate-50 text-slate-700 border-slate-200';
}

function Badge({ value }: { value: string }) {
  return <span className={`inline-flex items-center rounded border px-2 py-1 text-xs font-semibold ${statusClass(value)}`}>{value}</span>;
}

function Kpi({ icon: Icon, label, value, tone }: { icon: any; label: string; value: string; tone: string }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <div className={`grid h-11 w-11 place-items-center rounded-lg ${tone}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1 text-sm font-semibold text-slate-700">
      {label}
      {children}
    </label>
  );
}

function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-teal-600" />;
}

function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-teal-600" />;
}

export default function BanksDashboard() {
  const [authenticated, setAuthenticated] = useState(false);
  const [key, setKey] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('resumen');
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [movementAccountFilter, setMovementAccountFilter] = useState<string>('');
  const [accountModalOpen, setAccountModalOpen] = useState(false);
  const [movementModalOpen, setMovementModalOpen] = useState(false);
  const emptyAccountForm = {
    account_name: '',
    account_type: 'bank',
    bank_name: '',
    account_number: '',
    account_number_mask: '',
    clabe: '',
    holder_name: '',
    currency: 'MXN',
    responsible_user: '',
    opening_balance: '0',
    status: 'active',
    notes: ''
  };
  const [accountForm, setAccountForm] = useState(emptyAccountForm);
  const emptyMovementForm = {
    movement_kind: 'deposito',
    origin_account_id: '',
    destination_account_id: '',
    third_party_account_id: 'manual',
    third_party_name: '',
    third_party_account: '',
    third_party_clabe: '',
    performed_by: '',
    source_type: 'pago',
    amount: '',
    movement_date: today(),
    notes: ''
  };
  const [movementForm, setMovementForm] = useState(emptyMovementForm);

  const authByMovement = useMemo(() => {
    const map = new Map<string, Authorization>();
    data.authorizations.forEach((auth) => map.set(auth.movement_id, auth));
    return map;
  }, [data.authorizations]);

  const pendingAuthorizations = data.authorizations.filter((auth) => auth.status === 'pendiente');
  const pendingReconciliation = data.movements.filter((movement) => movement.reconciliation_status === 'pendiente' && movement.authorization_status !== 'rechazado');

  useEffect(() => {
    const saved = getStoredKey();
    if (saved) {
      setAuthenticated(true);
      void refresh();
    }
  }, []);

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const result = await banksApi<DashboardData>('dashboard');
      setData(result);
      if (!movementForm.destination_account_id && result.accounts[0]) {
        setMovementForm((current) => ({ ...current, destination_account_id: result.accounts[0].id }));
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando datos');
      if (String(err.message || '').includes('Clave')) {
        setAuthenticated(false);
        clearKey();
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await login(key);
      setAuthenticated(true);
      await refresh();
    } catch (err: any) {
      setError(err.message || 'Clave invalida');
    } finally {
      setSaving(false);
    }
  }

  async function createAccount(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await banksApi<Account>('create_account', accountForm);
      setAccountForm(emptyAccountForm);
      await refresh();
      setAccountModalOpen(false);
      setActiveTab('cuentas');
    } catch (err: any) {
      setError(err.message || 'No se pudo crear cuenta');
    } finally {
      setSaving(false);
    }
  }

  async function createMovement(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await banksApi('record_movement', movementForm);
      setMovementForm((current) => ({ ...current, amount: '', notes: '', movement_date: today(), third_party_name: '', third_party_account: '', third_party_clabe: '', performed_by: '' }));
      await refresh();
      setMovementModalOpen(false);
      setActiveTab('movimientos');
    } catch (err: any) {
      setError(err.message || 'No se pudo registrar movimiento');
    } finally {
      setSaving(false);
    }
  }

  async function decide(auth: Authorization, decision: 'aprobado' | 'rechazado') {
    setSaving(true);
    setError('');
    try {
      await banksApi('decide_authorization', { authorization_id: auth.id, decision, decision_notes: `Decision desde ${projectContext.service_name}` });
      await refresh();
    } catch (err: any) {
      setError(err.message || 'No se pudo decidir autorizacion');
    } finally {
      setSaving(false);
    }
  }

  async function reconcile(movement: Movement) {
    setSaving(true);
    setError('');
    try {
      await banksApi('mark_reconciled', { movement_id: movement.id, reconciliation_status: 'conciliado' });
      await refresh();
    } catch (err: any) {
      setError(err.message || 'No se pudo conciliar');
    } finally {
      setSaving(false);
    }
  }

  function openAccountMovements(account: Account) {
    setMovementAccountFilter(account.id);
    setMovementForm((current) => ({ ...current, destination_account_id: account.id, origin_account_id: account.id }));
    setActiveTab('movimientos');
  }

  if (!authenticated) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#eef2f4] px-4 py-10">
        <form onSubmit={handleLogin} className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-teal-50 text-teal-700">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-950">UC101 Bancos</h1>
              <p className="text-sm text-slate-500">Acceso operativo</p>
            </div>
          </div>
          <Field label="Clave">
            <TextInput value={key} type="password" autoFocus onChange={(event) => setKey(event.target.value)} placeholder="Clave de dashboard" />
          </Field>
          {error ? <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <button disabled={saving} className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Entrar
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#eef2f4]">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-lg bg-teal-50 text-teal-700">
              <Landmark className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-950">UC101 Bancos</h1>
              <p className="text-sm text-slate-500">{projectContext.company_id} / {projectContext.project_code} / {projectContext.schema}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => void refresh()} disabled={loading} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Actualizar
            </button>
            <button onClick={() => { clearKey(); setAuthenticated(false); }} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm">
              <LogOut className="h-4 w-4" />
              Salir
            </button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-5 py-5">
        {error ? <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div> : null}

        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Kpi icon={CircleDollarSign} label="Saldo total" value={money(data.kpis.total_balance)} tone="bg-teal-50 text-teal-700" />
          <Kpi icon={Landmark} label="Cuentas activas" value={String(data.kpis.active_accounts)} tone="bg-slate-100 text-slate-700" />
          <Kpi icon={ShieldCheck} label="Por autorizar" value={String(data.kpis.pending_authorizations)} tone="bg-amber-50 text-amber-700" />
          <Kpi icon={BadgeCheck} label="Por conciliar" value={String(data.kpis.pending_reconciliation)} tone="bg-cyan-50 text-cyan-700" />
          <Kpi icon={Banknote} label="Entradas mes" value={money(data.kpis.month_in)} tone="bg-emerald-50 text-emerald-700" />
          <Kpi icon={Banknote} label="Salidas mes" value={money(data.kpis.month_out)} tone="bg-rose-50 text-rose-700" />
        </div>

        <nav className="mt-5 flex gap-2 overflow-x-auto border-b border-slate-200">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`h-11 whitespace-nowrap border-b-2 px-3 text-sm font-semibold ${activeTab === tab.id ? 'border-teal-700 text-teal-800' : 'border-transparent text-slate-500'}`}>
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === 'resumen' ? <Resumen accounts={data.accounts} onOpenMovements={openAccountMovements} /> : null}
        {activeTab === 'cuentas' ? <Cuentas accounts={data.accounts} form={accountForm} setForm={setAccountForm} onSubmit={createAccount} saving={saving} modalOpen={accountModalOpen} setModalOpen={setAccountModalOpen} /> : null}
        {activeTab === 'movimientos' ? <Movimientos accounts={data.accounts} movements={data.movements} form={movementForm} setForm={setMovementForm} onSubmit={createMovement} saving={saving} accountFilter={movementAccountFilter} setAccountFilter={setMovementAccountFilter} modalOpen={movementModalOpen} setModalOpen={setMovementModalOpen} /> : null}
        {activeTab === 'autorizaciones' ? <Autorizaciones auths={pendingAuthorizations} movements={data.movements} onDecide={decide} saving={saving} /> : null}
        {activeTab === 'conciliacion' ? <Conciliacion accounts={data.accounts} movements={pendingReconciliation} authByMovement={authByMovement} onReconcile={reconcile} saving={saving} /> : null}
        {activeTab === 'conciliacion_gastos' ? <ConciliacionGastos accounts={data.accounts} onRefreshBanks={refresh} /> : null}
        {activeTab === 'converter' ? <ConverterTab /> : null}
      </section>
    </main>
  );
}

function Resumen({ accounts, onOpenMovements }: { accounts: Account[]; onOpenMovements: (account: Account) => void }) {
  return (
    <section className="mt-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {accounts.map((account) => (
          <article key={account.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-base font-bold text-slate-950">{account.account_name}</p>
                <p className="mt-1 text-sm font-semibold text-slate-600">{account.bank_name || 'Banco sin nombre'}</p>
              </div>
              <Badge value={account.status} />
            </div>
            <div className="mt-4 grid gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Numero de cuenta</p>
                <p className="mt-1 text-sm font-bold text-slate-800">{account.account_number_mask || '-'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Folio</p>
                <p className="mt-1 text-sm font-bold text-slate-800">{account.folio}</p>
              </div>
            </div>
            <div className="mt-4 flex items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Saldo</p>
                <p className="mt-1 text-2xl font-bold text-slate-950">{money(account.current_balance)}</p>
              </div>
              <button onClick={() => onOpenMovements(account)} className="inline-flex h-10 items-center gap-2 rounded-md bg-teal-700 px-3 text-sm font-semibold text-white shadow-sm hover:bg-teal-800">
                Movimientos
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </article>
        ))}
      </div>
      {!accounts.length ? <Empty text="Sin cuentas todavia" /> : null}
    </section>
  );
}

function Cuentas({ accounts, form, setForm, onSubmit, saving, modalOpen, setModalOpen }: any) {
  return (
    <section className="mt-5">
      <Panel title={
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <span>Cuentas registradas</span>
          <button onClick={() => setModalOpen(true)} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
            <Plus className="h-4 w-4" />
            Nueva cuenta
          </button>
        </div>
      }>
        <AccountTable accounts={accounts} />
      </Panel>
      {modalOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/45 px-3 py-4">
          <div className="flex max-h-[92vh] w-full max-w-md flex-col rounded-lg border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <h2 className="text-base font-bold text-slate-950">Nueva cuenta</h2>
              <button onClick={() => setModalOpen(false)} className="grid h-8 w-8 place-items-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50" aria-label="Cerrar">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
                <div className="grid gap-2">
                  <Field label="Nombre interno">
                    <TextInput required value={form.account_name} onChange={(event) => setForm({ ...form, account_name: event.target.value })} placeholder="BBVA principal" />
                  </Field>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Banco">
                      <TextInput required value={form.bank_name} onChange={(event) => setForm({ ...form, bank_name: event.target.value })} placeholder="BBVA" />
                    </Field>
                    <Field label="Tipo">
                      <Select value={form.account_type} onChange={(event) => setForm({ ...form, account_type: event.target.value })}>
                        <option value="bank">Bancaria</option>
                        <option value="cash">Caja</option>
                        <option value="wallet">Wallet</option>
                        <option value="review">Revision</option>
                      </Select>
                    </Field>
                  </div>
                  <Field label="Titular">
                    <TextInput value={form.holder_name} onChange={(event) => setForm({ ...form, holder_name: event.target.value })} placeholder="Razon social / titular" />
                  </Field>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Cuenta">
                      <TextInput value={form.account_number} onChange={(event) => setForm({ ...form, account_number: event.target.value })} placeholder="Numero completo" />
                    </Field>
                    <Field label="Visible">
                      <TextInput value={form.account_number_mask} onChange={(event) => setForm({ ...form, account_number_mask: event.target.value })} placeholder="****1234" />
                    </Field>
                  </div>
                  <Field label="Cuenta CLABE">
                    <TextInput value={form.clabe} onChange={(event) => setForm({ ...form, clabe: event.target.value })} placeholder="18 digitos" />
                  </Field>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Moneda">
                      <Select value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })}>
                        <option value="MXN">MXN</option>
                        <option value="USD">USD</option>
                      </Select>
                    </Field>
                    <Field label="Estado">
                      <Select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                        <option value="active">Activa</option>
                        <option value="inactive">Desactivada</option>
                        <option value="closed">Cerrada</option>
                      </Select>
                    </Field>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Saldo inicial">
                      <TextInput type="number" step="0.01" value={form.opening_balance} onChange={(event) => setForm({ ...form, opening_balance: event.target.value })} />
                    </Field>
                    <Field label="Responsable">
                      <TextInput value={form.responsible_user} onChange={(event) => setForm({ ...form, responsible_user: event.target.value })} placeholder="Usuario" />
                    </Field>
                  </div>
                  <Field label="Notas">
                    <TextInput value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Uso de la cuenta" />
                  </Field>
                </div>
              </div>
              <div className="border-t border-slate-200 bg-white px-4 py-3">
                <SaveButton saving={saving} label="Crear cuenta" />
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Movimientos({ accounts, movements, form, setForm, onSubmit, saving, accountFilter, setAccountFilter, modalOpen, setModalOpen }: any) {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const filteredMovements = movements.filter((movement: Movement) => {
    if (accountFilter && movement.account_id !== accountFilter) return false;
    if (dateFrom && movement.movement_date < dateFrom) return false;
    if (dateTo && movement.movement_date > dateTo) return false;
    return true;
  });
  const selectedAccount = accounts.find((account: Account) => account.id === accountFilter);
  const isDeposit = form.movement_kind === 'deposito';
  return (
    <section className="mt-5">
      <Panel title={
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <span>{selectedAccount ? `Movimientos - ${selectedAccount.account_name}` : 'Movimientos recientes'}</span>
          <div className="flex flex-col gap-2 lg:flex-row">
            <Select value={accountFilter || ''} onChange={(event) => setAccountFilter(event.target.value)} aria-label="Filtrar movimientos por cuenta">
              <option value="">Todas las cuentas</option>
              {accounts.map((account: Account) => <option key={account.id} value={account.id}>{account.account_name} / {account.folio}</option>)}
            </Select>
            <TextInput type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} aria-label="Fecha inicial" />
            <TextInput type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} aria-label="Fecha final" />
            <button onClick={() => setModalOpen(true)} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
              <Plus className="h-4 w-4" />
              Nuevo movimiento
            </button>
          </div>
        </div>
      }>
        <MovementTable accounts={accounts} movements={filteredMovements} />
      </Panel>
      {modalOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/45 px-3 py-4">
          <div className="flex max-h-[92vh] w-full max-w-md flex-col rounded-lg border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <h2 className="text-base font-bold text-slate-950">Nuevo movimiento</h2>
              <button onClick={() => setModalOpen(false)} className="grid h-8 w-8 place-items-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50" aria-label="Cerrar">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
                <div className="grid gap-2">
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Tipo">
                      <Select value={form.movement_kind} onChange={(event) => setForm({ ...form, movement_kind: event.target.value })}>
                        <option value="deposito">Deposito</option>
                        <option value="retiro">Retiro</option>
                      </Select>
                    </Field>
                    <Field label="Origen">
                      <Select value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value })}>
                        <option value="pago">Pago</option>
                        <option value="ajuste">Ajuste</option>
                        <option value="apertura">Apertura</option>
                        <option value="devolucion">Devolucion</option>
                      </Select>
                    </Field>
                  </div>
                  {!isDeposit ? (
                    <Field label="Cuenta origen propia">
                      <Select required value={form.origin_account_id} onChange={(event) => setForm({ ...form, origin_account_id: event.target.value })}>
                        <option value="">Seleccionar</option>
                        {accounts.map((account: Account) => <option key={account.id} value={account.id}>{account.account_name} / {account.folio}</option>)}
                      </Select>
                    </Field>
                  ) : null}
                  {isDeposit ? (
                    <Field label="Cuenta destino propia">
                      <Select required value={form.destination_account_id} onChange={(event) => setForm({ ...form, destination_account_id: event.target.value })}>
                        <option value="">Seleccionar</option>
                        {accounts.map((account: Account) => <option key={account.id} value={account.id}>{account.account_name} / {account.folio}</option>)}
                      </Select>
                    </Field>
                  ) : null}
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
                    <Field label={isDeposit ? 'Cuenta tercero origen' : 'Cuenta tercero destino'}>
                      <Select value={form.third_party_account_id} onChange={(event) => setForm({ ...form, third_party_account_id: event.target.value })}>
                        <option value="manual">Captura manual</option>
                      </Select>
                    </Field>
                    <div className="mt-2 grid gap-2">
                      <Field label="Nombre tercero">
                        <TextInput value={form.third_party_name} onChange={(event) => setForm({ ...form, third_party_name: event.target.value })} placeholder="Nombre / razon social" />
                      </Field>
                      <div className="grid grid-cols-2 gap-2">
                        <Field label="Cuenta tercero">
                          <TextInput value={form.third_party_account} onChange={(event) => setForm({ ...form, third_party_account: event.target.value })} placeholder="Cuenta" />
                        </Field>
                        <Field label="CLABE tercero">
                          <TextInput value={form.third_party_clabe} onChange={(event) => setForm({ ...form, third_party_clabe: event.target.value })} placeholder="CLABE" />
                        </Field>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Monto">
                      <TextInput required type="number" min="0.01" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
                    </Field>
                    <Field label="Fecha">
                      <TextInput required type="date" value={form.movement_date} onChange={(event) => setForm({ ...form, movement_date: event.target.value })} />
                    </Field>
                  </div>
                  <Field label="Notas">
                    <TextInput value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Referencia interna" />
                  </Field>
                  <Field label="Quien realizo">
                    <TextInput value={form.performed_by} onChange={(event) => setForm({ ...form, performed_by: event.target.value })} placeholder="Nombre del usuario" />
                  </Field>
                </div>
              </div>
              <div className="border-t border-slate-200 bg-white px-4 py-3">
                <SaveButton saving={saving} label="Registrar" />
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Autorizaciones({ auths, movements, onDecide, saving }: { auths: Authorization[]; movements: Movement[]; onDecide: (auth: Authorization, decision: 'aprobado' | 'rechazado') => void; saving: boolean }) {
  const movementMap = new Map(movements.map((movement) => [movement.id, movement]));
  return (
    <Panel title="Pendientes de autorizacion">
      <div className="grid gap-3">
        {auths.map((auth) => {
          const movement = movementMap.get(auth.movement_id);
          return (
            <div key={auth.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-bold text-slate-950">{auth.folio} / {movement?.folio || auth.movement_id}</p>
                  <p className="text-sm text-slate-500">{movement?.source_type || 'movimiento'} / {movement ? money(movement.amount) : ''}</p>
                </div>
                <div className="flex gap-2">
                  <button disabled={saving} onClick={() => onDecide(auth, 'aprobado')} className="inline-flex h-9 items-center gap-2 rounded-md bg-emerald-700 px-3 text-sm font-semibold text-white">
                    <CheckCircle2 className="h-4 w-4" />
                    Aprobar
                  </button>
                  <button disabled={saving} onClick={() => onDecide(auth, 'rechazado')} className="inline-flex h-9 items-center gap-2 rounded-md bg-rose-700 px-3 text-sm font-semibold text-white">
                    <XCircle className="h-4 w-4" />
                    Rechazar
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        {!auths.length ? <Empty text="Sin autorizaciones pendientes" /> : null}
      </div>
    </Panel>
  );
}

function accountLabel(accounts: Account[], accountId?: string | null, fallback?: string | null) {
  const account = accounts.find((row) => row.id === accountId);
  return account?.account_name || fallback || '-';
}

function movementOrigin(accounts: Account[], movement: Movement) {
  if (movement.movement_type === 'salida') {
    return accountLabel(accounts, movement.metadata?.origin_account_id || movement.account_id, movement.account_folio);
  }
  return movement.metadata?.third_party_name || movement.metadata?.third_party_account || 'Tercero';
}

function movementDestination(accounts: Account[], movement: Movement) {
  if (movement.movement_type === 'entrada') {
    return accountLabel(accounts, movement.metadata?.destination_account_id || movement.account_id, movement.account_folio);
  }
  return movement.metadata?.third_party_name || movement.metadata?.third_party_account || 'Tercero';
}

function movementKindLabel(movement: Movement) {
  return movement.metadata?.movement_kind || (movement.movement_type === 'entrada' ? 'deposito' : 'retiro');
}

function Conciliacion({ accounts, movements, authByMovement, onReconcile, saving }: { accounts: Account[]; movements: Movement[]; authByMovement: Map<string, Authorization>; onReconcile: (movement: Movement) => void; saving: boolean }) {
  return (
    <Panel title="Movimientos por conciliar">
      <div className="grid gap-3">
        {movements.map((movement) => (
          <div key={movement.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-bold text-slate-950">{movement.folio} / {money(movement.amount)}</p>
                <div className="mt-2 grid gap-1 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-4">
                  <span><b>Origen:</b> {movementOrigin(accounts, movement)}</span>
                  <span><b>Destino:</b> {movementDestination(accounts, movement)}</span>
                  <span><b>Tipo:</b> {movementKindLabel(movement)}</span>
                  <span><b>Realizo:</b> {movement.metadata?.performed_by || '-'}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{movement.movement_date} / {authByMovement.get(movement.id)?.folio || 'sin autorizacion'}</p>
              </div>
              <button disabled={saving} onClick={() => onReconcile(movement)} className="inline-flex h-9 items-center gap-2 rounded-md bg-teal-700 px-3 text-sm font-semibold text-white">
                <BadgeCheck className="h-4 w-4" />
                Conciliar
              </button>
            </div>
          </div>
        ))}
        {!movements.length ? <Empty text="Sin movimientos pendientes" /> : null}
      </div>
    </Panel>
  );
}

function ConciliacionGastos({ accounts, onRefreshBanks }: { accounts: Account[]; onRefreshBanks: () => Promise<void> }) {
  const [data, setData] = useState<ExpenseReconciliationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [accountByExpense, setAccountByExpense] = useState<Record<string, string>>({});
  const [err, setErr] = useState('');

  useEffect(() => { void load(); }, []);

  async function load() {
    setLoading(true);
    setErr('');
    try {
      const result = await banksApi<ExpenseReconciliationData>('list_expense_reconciliation', { limit: 300 });
      setData(result);
      const defaultId = result.default_source_account?.id || accounts.find((account) => account.account_name === (projectContext as any).default_expense_source_account_name)?.id || '';
      if (defaultId) {
        const next: Record<string, string> = {};
        for (const expense of result.expenses) next[expense.id] = defaultId;
        setAccountByExpense(next);
      }
    } catch (error: any) {
      setErr(error.message || 'No se pudieron cargar gastos');
    } finally {
      setLoading(false);
    }
  }

  async function assign(expense: ExpenseReconciliationRow) {
    const sourceAccountId = accountByExpense[expense.id] || data?.default_source_account?.id || '';
    if (!sourceAccountId) {
      setErr('Selecciona cuenta origen para registrar el retiro');
      return;
    }
    setAssigningId(expense.id);
    setErr('');
    try {
      await banksApi('assign_expense_withdrawal', {
        expense_id: expense.id,
        source_account_id: sourceAccountId,
        performed_by: 'conciliacion_gastos',
        notes: expense.descripcion || expense.folio
      });
      await load();
      await onRefreshBanks();
    } catch (error: any) {
      setErr(error.message || 'No se pudo asignar gasto');
    } finally {
      setAssigningId(null);
    }
  }

  const expenses = data?.expenses || [];
  const pending = expenses.filter((expense) => !expense.linked);

  return (
    <section className="mt-5">
      <Panel title={
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <span>Conciliacion de gastos</span>
          <button onClick={() => void load()} disabled={loading} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Actualizar
          </button>
        </div>
      }>
        {err ? <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{err}</div> : null}
        <div className="mb-4 grid gap-3 md:grid-cols-3">
          <Kpi icon={FileText} label="Gastos leidos" value={String(data?.summary.total || 0)} tone="bg-slate-100 text-slate-700" />
          <Kpi icon={BadgeCheck} label="Pendientes" value={String(data?.summary.pending || 0)} tone="bg-amber-50 text-amber-700" />
          <Kpi icon={CheckCircle2} label="Asignados" value={String(data?.summary.linked || 0)} tone="bg-emerald-50 text-emerald-700" />
        </div>
        {!pending.length && !loading ? <Empty text="Sin gastos pendientes por asignar" /> : null}
        {pending.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] border-separate border-spacing-0 text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-normal text-slate-500">
                  <th className="border-b border-slate-200 px-3 py-2">Gasto</th>
                  <th className="border-b border-slate-200 px-3 py-2">Fecha</th>
                  <th className="border-b border-slate-200 px-3 py-2">Descripcion</th>
                  <th className="border-b border-slate-200 px-3 py-2">Vehiculo</th>
                  <th className="border-b border-slate-200 px-3 py-2 text-right">Monto</th>
                  <th className="border-b border-slate-200 px-3 py-2">Cuenta origen</th>
                  <th className="border-b border-slate-200 px-3 py-2">Destino</th>
                  <th className="border-b border-slate-200 px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {pending.map((expense) => (
                  <tr key={expense.id}>
                    <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">{expense.folio}</td>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{expense.fecha}</td>
                    <td className="max-w-xs truncate border-b border-slate-100 px-3 py-3 text-slate-600">{expense.descripcion || '-'}</td>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{expense.vehiculo || '-'}</td>
                    <td className="border-b border-slate-100 px-3 py-3 text-right font-bold text-rose-700">{money(expense.monto)}</td>
                    <td className="border-b border-slate-100 px-3 py-3">
                      <Select value={accountByExpense[expense.id] || ''} onChange={(event) => setAccountByExpense({ ...accountByExpense, [expense.id]: event.target.value })}>
                        <option value="">Seleccionar</option>
                        {accounts.map((account) => <option key={account.id} value={account.id}>{account.account_name}</option>)}
                      </Select>
                    </td>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{data?.expense_counterparty_name || 'Gastos'}</td>
                    <td className="border-b border-slate-100 px-3 py-3">
                      <button disabled={assigningId === expense.id} onClick={() => void assign(expense)} className="inline-flex h-9 items-center gap-2 rounded-md bg-teal-700 px-3 text-sm font-semibold text-white">
                        {assigningId === expense.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                        Asignar retiro
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
    </section>
  );
}

function Panel({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-4 text-base font-bold text-slate-950">{title}</h2>
      {children}
    </section>
  );
}

function SaveButton({ saving, label }: { saving: boolean; label: string }) {
  return (
    <button disabled={saving} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      {label}
    </button>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm font-semibold text-slate-500">{text}</div>;
}

function AccountTable({ accounts }: { accounts: Account[] }) {
  if (!accounts.length) return <Empty text="Sin cuentas registradas" />;
  return (
    <div className="grid gap-3">
      {accounts.map((account) => (
        <article key={account.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-bold text-slate-950">{account.account_name}</h3>
                <Badge value={account.status} />
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-600">{account.bank_name || 'Banco sin nombre'} / {account.account_type}</p>
              <p className="mt-1 text-xs text-slate-500">{account.folio}</p>
            </div>
            <div className="lg:text-right">
              <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Saldo actual</p>
              <p className="mt-1 text-2xl font-bold text-slate-950">{money(account.current_balance)}</p>
              <p className="mt-1 text-xs text-slate-500">Inicial {money(account.opening_balance)} / {account.currency}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3 md:grid-cols-2 xl:grid-cols-4">
            <InfoBlock label="Cuenta" value={account.account_number || account.account_number_mask || '-'} />
            <InfoBlock label="Cuenta visible" value={account.account_number_mask || '-'} />
            <InfoBlock label="CLABE" value={account.metadata?.clabe || '-'} />
            <InfoBlock label="Titular" value={account.holder_name || '-'} />
            <InfoBlock label="Responsable" value={account.responsible_user || '-'} />
            <InfoBlock label="Notas" value={account.metadata?.notes || '-'} />
          </div>
        </article>
      ))}
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-bold text-slate-800" title={value}>{value}</p>
    </div>
  );
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function downloadBase64(b64: string, filename: string, mime: string) {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  const blob = new Blob([arr], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

type UploadResult = { dry_run: boolean; idempotent: boolean; extraction: { id: string; folio: string }; lines_created: number };

function ConverterTab() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [extractions, setExtractions] = useState<StatementExtraction[]>([]);
  const [loadingExtractions, setLoadingExtractions] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [lines, setLines] = useState<StatementLine[]>([]);
  const [loadingLines, setLoadingLines] = useState(false);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingExtraction, setEditingExtraction] = useState<StatementExtraction | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [editSaving, setEditSaving] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => { void loadExtractions(); }, []);

  async function loadExtractions() {
    setLoadingExtractions(true);
    setErr('');
    try {
      const data = await banksApi<StatementExtraction[]>('list_statements');
      setExtractions(data || []);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoadingExtractions(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setErr('');
    try {
      const b64 = await toBase64(file);
      const result = await banksApi<UploadResult>('upload_statement', { pdf_content: b64, file_name: file.name });
      setUploadResult(result);
      (e.target as HTMLFormElement).reset();
      setFile(null);
      await loadExtractions();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSelect(id: string) {
    if (selectedId === id) { setSelectedId(null); return; }
    setSelectedId(id);
    setLoadingLines(true);
    setErr('');
    try {
      const data = await banksApi<StatementLine[]>('statement_lines', { extraction_id: id });
      setLines(data || []);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoadingLines(false);
    }
  }

  async function handleDelete(id: string, folio: string) {
    if (!window.confirm(`¿Borrar extracción ${folio}? Se eliminarán todas sus líneas.`)) return;
    setDeletingId(id);
    setErr('');
    try {
      await banksApi('delete_statement', { extraction_id: id });
      if (selectedId === id) { setSelectedId(null); setLines([]); }
      await loadExtractions();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleEditSave() {
    if (!editingExtraction) return;
    setEditSaving(true);
    setErr('');
    try {
      await banksApi('update_statement', { extraction_id: editingExtraction.id, ...editForm });
      setEditingExtraction(null);
      await loadExtractions();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setEditSaving(false);
    }
  }

  async function handleExcel(id: string) {
    setExportingId(id);
    setErr('');
    try {
      const result = await banksApi<{ xlsx_base64: string; filename: string }>('export_excel', { extraction_id: id });
      downloadBase64(result.xlsx_base64, result.filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setExportingId(null);
    }
  }

  const selectedExtraction = extractions.find((ex) => ex.id === selectedId);
  const totalDepositos = lines.filter((ln) => ln.direction === 'deposito').reduce((sum, ln) => sum + Math.abs(ln.amount), 0);
  const totalRetiros = lines.filter((ln) => ln.direction !== 'deposito').reduce((sum, ln) => sum + Math.abs(ln.amount), 0);
  const stmtBalance = totalDepositos - totalRetiros;

  return (
    <section className="mt-5 grid gap-5">
      {err ? <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{err}</div> : null}

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <Panel title={<div className="flex items-center gap-2"><FileText className="h-4 w-4 text-teal-700" /><span>Subir PDF</span></div>}>
          <form onSubmit={handleUpload} className="grid gap-3">
            <Field label="Archivo (Banorte / BBVA)">
              <input
                type="file"
                accept=".pdf"
                required
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm file:mr-3 file:border-0 file:bg-teal-50 file:text-xs file:font-semibold file:text-teal-700"
              />
            </Field>
            <SaveButton saving={uploading} label="Procesar PDF" />
          </form>
          {uploadResult ? (
            <div className={`mt-4 rounded-lg border p-3 ${uploadResult.idempotent ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}>
              <p className="text-sm font-bold text-slate-950">{uploadResult.extraction.folio}</p>
              <p className="mt-1 text-xs text-slate-600">
                {uploadResult.idempotent ? 'Ya existia — no se duplico' : `${uploadResult.lines_created} líneas extraídas`}
              </p>
            </div>
          ) : null}
        </Panel>

        <Panel title={
          <div className="flex items-center justify-between">
            <span>Extracciones</span>
            <button
              onClick={() => void loadExtractions()}
              disabled={loadingExtractions}
              className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              {loadingExtractions ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
              Actualizar
            </button>
          </div>
        }>
          {!extractions.length && !loadingExtractions
            ? <Empty text="Sin extracciones todavía — sube un PDF" />
            : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[740px] border-separate border-spacing-0 text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-normal text-slate-500">
                      <th className="border-b border-slate-200 px-3 py-2">Folio</th>
                      <th className="border-b border-slate-200 px-3 py-2">Banco</th>
                      <th className="border-b border-slate-200 px-3 py-2">Titular</th>
                      <th className="border-b border-slate-200 px-3 py-2">Cuenta</th>
                      <th className="border-b border-slate-200 px-3 py-2">Periodo</th>
                      <th className="border-b border-slate-200 px-3 py-2">Líneas</th>
                      <th className="border-b border-slate-200 px-3 py-2">Validación</th>
                      <th className="border-b border-slate-200 px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractions.map((ex) => (
                      <tr key={ex.id} className={selectedId === ex.id ? 'bg-teal-50' : undefined}>
                        <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">{ex.folio}</td>
                        <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{ex.bank_name || ex.bank_profile}</td>
                        <td className="border-b border-slate-100 px-3 py-3 text-slate-600 max-w-[160px]" title={ex.holder_name || ''}>
                          {editingExtraction?.id === ex.id
                            ? <input className="h-7 w-full rounded border border-slate-300 px-2 text-xs" value={editForm.holder_name || ''} onChange={(e) => setEditForm({ ...editForm, holder_name: e.target.value })} />
                            : <span className="block truncate">{ex.holder_name || '—'}</span>}
                        </td>
                        <td className="border-b border-slate-100 px-3 py-3 text-slate-600 font-mono text-xs">
                          {editingExtraction?.id === ex.id
                            ? <input className="h-7 w-28 rounded border border-slate-300 px-2 text-xs font-mono" value={editForm.account_number_mask || ''} onChange={(e) => setEditForm({ ...editForm, account_number_mask: e.target.value })} />
                            : ex.account_number_mask || '—'}
                        </td>
                        <td className="border-b border-slate-100 px-3 py-3 text-slate-600 text-xs">
                          {editingExtraction?.id === ex.id
                            ? <div className="flex gap-1">
                                <input type="date" className="h-7 rounded border border-slate-300 px-1 text-xs" value={editForm.statement_period_start || ''} onChange={(e) => setEditForm({ ...editForm, statement_period_start: e.target.value })} />
                                <input type="date" className="h-7 rounded border border-slate-300 px-1 text-xs" value={editForm.statement_period_end || ''} onChange={(e) => setEditForm({ ...editForm, statement_period_end: e.target.value })} />
                              </div>
                            : ex.statement_period_start && ex.statement_period_end
                              ? `${ex.statement_period_start} → ${ex.statement_period_end}`
                              : '—'}
                        </td>
                        <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{ex.total_lines_extracted}</td>
                        <td className="border-b border-slate-100 px-3 py-3"><Badge value={ex.validation_status} /></td>
                        <td className="border-b border-slate-100 px-3 py-3">
                          {editingExtraction?.id === ex.id ? (
                            <div className="flex gap-1">
                              <button
                                onClick={() => void handleEditSave()}
                                disabled={editSaving}
                                className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2 text-xs font-semibold text-white disabled:opacity-50"
                              >
                                {editSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                                Guardar
                              </button>
                              <button
                                onClick={() => setEditingExtraction(null)}
                                className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 px-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex gap-1">
                              <button
                                onClick={() => void handleSelect(ex.id)}
                                className={`inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-semibold ${selectedId === ex.id ? 'bg-teal-700 text-white' : 'border border-slate-300 text-slate-700 hover:bg-slate-50'}`}
                              >
                                {selectedId === ex.id ? 'Cerrar' : 'Ver'}
                              </button>
                              <button
                                onClick={() => {
                                  setEditingExtraction(ex);
                                  setEditForm({
                                    holder_name: ex.holder_name || '',
                                    account_number_mask: ex.account_number_mask || '',
                                    statement_period_start: ex.statement_period_start || '',
                                    statement_period_end: ex.statement_period_end || '',
                                  });
                                }}
                                className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 px-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                title="Editar campos"
                              >
                                <Pencil className="h-3 w-3" />
                              </button>
                              <button
                                onClick={() => void handleExcel(ex.id)}
                                disabled={exportingId === ex.id}
                                className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 px-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                              >
                                {exportingId === ex.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                                Excel
                              </button>
                              <button
                                onClick={() => void handleDelete(ex.id, ex.folio)}
                                disabled={deletingId === ex.id}
                                className="inline-flex h-7 items-center gap-1 rounded border border-rose-200 px-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                              >
                                {deletingId === ex.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </Panel>
      </div>


      {selectedId ? (
        <Panel title={`Movimientos — ${selectedExtraction?.folio || selectedId} · ${selectedExtraction?.bank_name || ''} · ${selectedExtraction?.statement_period_start || ''} → ${selectedExtraction?.statement_period_end || ''}`}>
          {lines.length > 0 ? (
            <div className="mb-4 grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-normal text-emerald-600">Total Depósitos</p>
                <p className="mt-1 text-xl font-bold text-emerald-700">{money(totalDepositos)}</p>
              </div>
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-normal text-rose-600">Total Retiros</p>
                <p className="mt-1 text-xl font-bold text-rose-700">{money(totalRetiros)}</p>
              </div>
              <div className={`rounded-lg border px-4 py-3 ${stmtBalance >= 0 ? 'border-teal-200 bg-teal-50' : 'border-amber-200 bg-amber-50'}`}>
                <p className="text-xs font-semibold uppercase tracking-normal text-slate-600">Balance del período</p>
                <p className={`mt-1 text-xl font-bold ${stmtBalance >= 0 ? 'text-teal-700' : 'text-amber-700'}`}>{money(stmtBalance)}</p>
              </div>
            </div>
          ) : null}
          {loadingLines
            ? <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-teal-700" /></div>
            : lines.length
              ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[860px] border-separate border-spacing-0 text-left text-[11px]">
                    <thead>
                      <tr className="uppercase tracking-normal text-slate-500" style={{fontSize:'10px'}}>
                        <th className="border-b border-slate-200 px-2 py-1 w-8">#</th>
                        <th className="border-b border-slate-200 px-2 py-1 whitespace-nowrap">Fecha</th>
                        <th className="border-b border-slate-200 px-2 py-1 whitespace-nowrap">Tipo</th>
                        <th className="border-b border-slate-200 px-2 py-1">Dir</th>
                        <th className="border-b border-slate-200 px-2 py-1 text-right whitespace-nowrap">Monto</th>
                        <th className="border-b border-slate-200 px-2 py-1 text-right whitespace-nowrap">Saldo</th>
                        <th className="border-b border-slate-200 px-2 py-1 text-right">Conf%</th>
                        <th className="border-b border-slate-200 px-2 py-1">Descripción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((ln) => (
                        <tr key={ln.id} className="hover:bg-slate-50">
                          <td className="border-b border-slate-100 px-2 py-1 text-slate-400">{ln.raw_line_order}</td>
                          <td className="border-b border-slate-100 px-2 py-1 text-slate-600 whitespace-nowrap">{ln.line_date}</td>
                          <td className="border-b border-slate-100 px-2 py-1 text-slate-500 whitespace-nowrap">{ln.metadata?.tipo_movimiento?.replace(/_/g,' ') || '—'}</td>
                          <td className="border-b border-slate-100 px-2 py-1">
                            <span className={`inline-flex rounded px-1 py-0.5 font-semibold ${ln.direction === 'deposito' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                              {ln.direction === 'deposito' ? 'DEP' : 'RET'}
                            </span>
                          </td>
                          <td className={`border-b border-slate-100 px-2 py-1 text-right font-bold ${ln.direction === 'deposito' ? 'text-emerald-700' : 'text-rose-700'}`}>
                            {money(ln.amount)}
                          </td>
                          <td className="border-b border-slate-100 px-2 py-1 text-right text-slate-600">
                            {ln.saldo != null ? money(ln.saldo) : '—'}
                          </td>
                          <td className={`border-b border-slate-100 px-2 py-1 text-right font-semibold ${ln.confidence >= 0.9 ? 'text-emerald-700' : ln.confidence >= 0.5 ? 'text-amber-700' : 'text-rose-700'}`}>
                            {Math.round((ln.confidence ?? 0) * 100)}%
                          </td>
                          <td className="border-b border-slate-100 px-2 py-1 text-slate-500">{ln.description || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
              : <Empty text="Sin movimientos cargados" />}
        </Panel>
      ) : null}
    </section>
  );
}

function MovementTable({ accounts, movements, compact = false }: { accounts: Account[]; movements: Movement[]; compact?: boolean }) {
  if (!movements.length) return <Empty text="Sin movimientos registrados" />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-normal text-slate-500">
            <th className="border-b border-slate-200 px-3 py-2">Folio</th>
            <th className="border-b border-slate-200 px-3 py-2">Fecha</th>
            <th className="border-b border-slate-200 px-3 py-2">Cuenta</th>
            <th className="border-b border-slate-200 px-3 py-2">Tipo</th>
            <th className="border-b border-slate-200 px-3 py-2">Monto</th>
            <th className="border-b border-slate-200 px-3 py-2">Auth</th>
            {!compact ? <th className="border-b border-slate-200 px-3 py-2">Conciliacion</th> : null}
          </tr>
        </thead>
        <tbody>
          {movements.map((movement) => (
            <tr key={movement.id}>
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">{movement.folio}</td>
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{movement.movement_date}</td>
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{accountLabel(accounts, movement.account_id, movement.account_folio)}</td>
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{movement.movement_type}</td>
              <td className={`border-b border-slate-100 px-3 py-3 font-bold ${movement.movement_type === 'entrada' ? 'text-emerald-700' : 'text-rose-700'}`}>{money(movement.amount)}</td>
              <td className="border-b border-slate-100 px-3 py-3"><Badge value={movement.authorization_status} /></td>
              {!compact ? <td className="border-b border-slate-100 px-3 py-3"><Badge value={movement.reconciliation_status} /></td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
