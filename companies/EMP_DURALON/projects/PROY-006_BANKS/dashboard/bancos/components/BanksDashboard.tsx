'use client';

import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import {
  BadgeCheck,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  KeyRound,
  Landmark,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
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
  type Movement
} from '../lib/api';
import projectContext from '../project-context.json';

type Tab = 'resumen' | 'cuentas' | 'movimientos' | 'autorizaciones' | 'conciliacion';

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
  { id: 'conciliacion', label: 'Conciliacion' }
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
  const [accountForm, setAccountForm] = useState({ account_name: '', bank_name: '', account_number_mask: '', opening_balance: '0' });
  const [movementForm, setMovementForm] = useState({
    account_id: '',
    movement_type: 'entrada',
    source_type: 'ajuste',
    amount: '',
    movement_date: today(),
    notes: ''
  });

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
      if (!movementForm.account_id && result.accounts[0]) {
        setMovementForm((current) => ({ ...current, account_id: result.accounts[0].id }));
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
      setAccountForm({ account_name: '', bank_name: '', account_number_mask: '', opening_balance: '0' });
      await refresh();
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
      setMovementForm((current) => ({ ...current, amount: '', notes: '', movement_date: today() }));
      await refresh();
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

        {activeTab === 'resumen' ? <Resumen accounts={data.accounts} movements={data.movements} /> : null}
        {activeTab === 'cuentas' ? <Cuentas accounts={data.accounts} form={accountForm} setForm={setAccountForm} onSubmit={createAccount} saving={saving} /> : null}
        {activeTab === 'movimientos' ? <Movimientos accounts={data.accounts} movements={data.movements} form={movementForm} setForm={setMovementForm} onSubmit={createMovement} saving={saving} /> : null}
        {activeTab === 'autorizaciones' ? <Autorizaciones auths={pendingAuthorizations} movements={data.movements} onDecide={decide} saving={saving} /> : null}
        {activeTab === 'conciliacion' ? <Conciliacion movements={pendingReconciliation} authByMovement={authByMovement} onReconcile={reconcile} saving={saving} /> : null}
      </section>
    </main>
  );
}

function Resumen({ accounts, movements }: { accounts: Account[]; movements: Movement[] }) {
  return (
    <section className="mt-5 grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
      <Panel title="Cuentas">
        <div className="grid gap-3">
          {accounts.map((account) => (
            <div key={account.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold text-slate-950">{account.account_name}</p>
                  <p className="text-sm text-slate-500">{account.bank_name || 'Banco'} / {account.folio}</p>
                </div>
                <Badge value={account.status} />
              </div>
              <p className="mt-3 text-2xl font-bold text-slate-950">{money(account.current_balance)}</p>
            </div>
          ))}
          {!accounts.length ? <Empty text="Sin cuentas todavia" /> : null}
        </div>
      </Panel>
      <Panel title="Ultimos movimientos">
        <MovementTable movements={movements.slice(0, 8)} compact />
      </Panel>
    </section>
  );
}

function Cuentas({ accounts, form, setForm, onSubmit, saving }: any) {
  return (
    <section className="mt-5 grid gap-5 lg:grid-cols-[360px_1fr]">
      <Panel title="Nueva cuenta">
        <form onSubmit={onSubmit} className="grid gap-3">
          <Field label="Nombre">
            <TextInput required value={form.account_name} onChange={(event) => setForm({ ...form, account_name: event.target.value })} placeholder="BBVA principal" />
          </Field>
          <Field label="Banco">
            <TextInput value={form.bank_name} onChange={(event) => setForm({ ...form, bank_name: event.target.value })} placeholder="Banco" />
          </Field>
          <Field label="Cuenta visible">
            <TextInput value={form.account_number_mask} onChange={(event) => setForm({ ...form, account_number_mask: event.target.value })} placeholder="****1234" />
          </Field>
          <Field label="Saldo inicial">
            <TextInput type="number" step="0.01" value={form.opening_balance} onChange={(event) => setForm({ ...form, opening_balance: event.target.value })} />
          </Field>
          <SaveButton saving={saving} label="Crear cuenta" />
        </form>
      </Panel>
      <Panel title="Cuentas registradas">
        <AccountTable accounts={accounts} />
      </Panel>
    </section>
  );
}

function Movimientos({ accounts, movements, form, setForm, onSubmit, saving }: any) {
  return (
    <section className="mt-5 grid gap-5 xl:grid-cols-[380px_1fr]">
      <Panel title="Nuevo movimiento">
        <form onSubmit={onSubmit} className="grid gap-3">
          <Field label="Cuenta">
            <Select required value={form.account_id} onChange={(event) => setForm({ ...form, account_id: event.target.value })}>
              <option value="">Seleccionar</option>
              {accounts.map((account: Account) => <option key={account.id} value={account.id}>{account.account_name} / {account.folio}</option>)}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo">
              <Select value={form.movement_type} onChange={(event) => setForm({ ...form, movement_type: event.target.value })}>
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
              </Select>
            </Field>
            <Field label="Origen">
              <Select value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value })}>
                <option value="ajuste">Ajuste</option>
                <option value="pago">Pago</option>
                <option value="transferencia">Transferencia</option>
                <option value="apertura">Apertura</option>
                <option value="devolucion">Devolucion</option>
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
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
          <SaveButton saving={saving} label="Registrar" />
        </form>
      </Panel>
      <Panel title="Movimientos recientes">
        <MovementTable movements={movements} />
      </Panel>
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

function Conciliacion({ movements, authByMovement, onReconcile, saving }: { movements: Movement[]; authByMovement: Map<string, Authorization>; onReconcile: (movement: Movement) => void; saving: boolean }) {
  return (
    <Panel title="Movimientos por conciliar">
      <div className="grid gap-3">
        {movements.map((movement) => (
          <div key={movement.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-bold text-slate-950">{movement.folio} / {money(movement.amount)}</p>
                <p className="text-sm text-slate-500">{movement.account_folio} / {movement.movement_date} / {authByMovement.get(movement.id)?.folio || 'sin autorizacion'}</p>
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

function Panel({ title, children }: { title: string; children: ReactNode }) {
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
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-normal text-slate-500">
            <th className="border-b border-slate-200 px-3 py-2">Cuenta</th>
            <th className="border-b border-slate-200 px-3 py-2">Banco</th>
            <th className="border-b border-slate-200 px-3 py-2">Folio</th>
            <th className="border-b border-slate-200 px-3 py-2">Saldo</th>
            <th className="border-b border-slate-200 px-3 py-2">Estado</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">{account.account_name}</td>
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{account.bank_name || '-'}</td>
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{account.folio}</td>
              <td className="border-b border-slate-100 px-3 py-3 font-bold text-slate-950">{money(account.current_balance)}</td>
              <td className="border-b border-slate-100 px-3 py-3"><Badge value={account.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MovementTable({ movements, compact = false }: { movements: Movement[]; compact?: boolean }) {
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
              <td className="border-b border-slate-100 px-3 py-3 text-slate-600">{movement.account_folio}</td>
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
