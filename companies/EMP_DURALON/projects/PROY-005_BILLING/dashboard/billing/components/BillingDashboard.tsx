'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ArrowDownCircle,
  ArrowUpCircle,
  Banknote,
  Calculator,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  CircleDollarSign,
  ClipboardList,
  Clock,
  ExternalLink,
  FileText,
  GitCompare,
  Loader2,
  Plus,
  Printer,
  RefreshCw,
  RotateCcw,
  Search,
  Users,
  WalletCards,
  XCircle,
} from 'lucide-react';
import * as api from '../lib/api';
import projectContext from '../project-context.json';
import type {
  Anticipo,
  CashCut,
  CashCutData,
  ClientRankingData,
  ClientStatementData,
  ConciliacionData,
  ConciliacionRow,
  Devolucion,
  MoneyAccount,
  Payment,
  PaymentApplication,
  Remision,
} from '../lib/api';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n?: number | null) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(n ?? 0);

const fmtDate = (d?: string | null) =>
  d ? new Date(d.length === 10 ? d + 'T12:00:00' : d).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: '2-digit' }) : '-';

const todayISO = () => new Date().toISOString().slice(0, 10);

const METODOS = ['efectivo', 'tarjeta', 'transferencia', 'deposito', 'cheque'];

const METODO_LABEL: Record<string, string> = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
  deposito: 'Depósito',
  cheque: 'Cheque',
};

function StatusBadge({ status }: { status?: string | null }) {
  const map: Record<string, string> = {
    pagada: 'bg-green-100 text-green-800',
    confirmado: 'bg-green-100 text-green-800',
    disponible: 'bg-blue-100 text-blue-800',
    por_confirmar: 'bg-yellow-100 text-yellow-800',
    pendiente: 'bg-yellow-100 text-yellow-800',
    parcial: 'bg-orange-100 text-orange-800',
    cancelada: 'bg-red-100 text-red-800',
    cancelado: 'bg-red-100 text-red-800',
    aplicado: 'bg-gray-100 text-gray-700',
    aprobada: 'bg-indigo-100 text-indigo-800',
  };
  const cls = map[status ?? ''] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status ?? '-'}
    </span>
  );
}

function Semaforo({ semaforo }: { semaforo: string }) {
  const color = semaforo === 'rojo' ? 'bg-red-500' : semaforo === 'amarillo' ? 'bg-yellow-400' : 'bg-green-500';
  return <span className={`inline-block w-3 h-3 rounded-full ${color}`} />;
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><XCircle size={20} /></button>
        </div>
        <div className="overflow-y-auto px-6 py-4 flex-1">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}

const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';
const btnPrimary = 'bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50';
const btnSecondary = 'border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg px-4 py-2 text-sm font-medium';

// ─── Tab type ─────────────────────────────────────────────────────────────────

type Tab = 'remisiones' | 'pagos' | 'anticipos' | 'devoluciones' | 'estado_cuenta' | 'clientes' | 'corte' | 'conciliacion';

const TABS: Array<{ id: Tab; label: string; Icon: typeof FileText }> = [
  { id: 'remisiones', label: 'Remisiones', Icon: FileText },
  { id: 'pagos', label: 'Pagos', Icon: Banknote },
  { id: 'anticipos', label: 'Anticipos', Icon: WalletCards },
  { id: 'devoluciones', label: 'Devoluciones', Icon: RotateCcw },
  { id: 'estado_cuenta', label: 'Estado de Cuenta', Icon: ClipboardList },
  { id: 'clientes', label: 'Clientes', Icon: Users },
  { id: 'corte', label: 'Corte de Caja', Icon: Calculator },
  { id: 'conciliacion', label: 'Conciliación', Icon: GitCompare },
];

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function BillingDashboard() {
  const [tab, setTab] = useState<Tab>('remisiones');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState<MoneyAccount[]>([]);

  // Tab 1 – Remisiones
  const [remisiones, setRemisiones] = useState<Remision[]>([]);
  const [remFilter, setRemFilter] = useState({ customer: '', status: '', date_from: '', date_to: '' });

  // Tab 2 – Pagos
  const [payments, setPayments] = useState<Payment[]>([]);
  const [paymentApplications, setPaymentApplications] = useState<PaymentApplication[]>([]);
  const [payFilter, setPayFilter] = useState({ customer: '', date_from: '', date_to: '', confirmation_status: '' });

  // Tab 3 – Anticipos
  const [anticipos, setAnticipos] = useState<Anticipo[]>([]);
  const [antFilter, setAntFilter] = useState({ customer: '', status: '' });

  // Tab 4 – Devoluciones
  const [devoluciones, setDevoluciones] = useState<Devolucion[]>([]);
  const [devFilter, setDevFilter] = useState({ customer: '', status: '' });

  // Tab 5 – Estado de Cuenta
  const [stmtQuery, setStmtQuery] = useState('');
  const [statement, setStatement] = useState<ClientStatementData | null>(null);

  // Tab 6 – Clientes
  const [ranking, setRanking] = useState<ClientRankingData | null>(null);
  const [rankFilter, setRankFilter] = useState<'todos' | '8' | '15' | '21'>('todos');
  const [rankSort, setRankSort] = useState<{ col: string; dir: 'desc' | 'asc' }>({ col: 'm_actual', dir: 'desc' });
  type ProductSlot = { input: string; stats: { label: string; por_cliente: Record<string, number> } | null; loading: boolean };
  const [slot1, setSlot1] = useState<ProductSlot>({ input: '', stats: null, loading: false });
  const [slot2, setSlot2] = useState<ProductSlot>({ input: '', stats: null, loading: false });

  // Tab 7 – Corte
  const [cutDate, setCutDate] = useState(todayISO());
  const [cutData, setCutData] = useState<CashCutData | null>(null);

  // Tab 8 – Conciliación
  const [concData, setConcData] = useState<ConciliacionData | null>(null);
  const [concFilter, setConcFilter] = useState({ date_from: '', date_to: '', account_id: '' });
  const [matchModal, setMatchModal] = useState<ConciliacionRow | null>(null);
  const [matchPayId, setMatchPayId] = useState('');
  const [matchSaving, setMatchSaving] = useState(false);

  // Modals
  type ModalState =
    | { kind: 'pago'; remision: Remision }
    | { kind: 'apply_pago'; payment: Payment }
    | { kind: 'confirm_pago'; payment: Payment }
    | { kind: 'nuevo_anticipo' }
    | { kind: 'apply_anticipo'; anticipo: Anticipo }
    | { kind: 'nueva_dev' }
    | { kind: 'resolve_dev'; devolucion: Devolucion }
    | { kind: 'close_corte'; cut: CashCut }
    | null;
  const [modal, setModal] = useState<ModalState>(null);

  // Form state (shared across modals)
  const [form, setForm] = useState<Record<string, string>>({});
  const [formErr, setFormErr] = useState('');
  const [saving, setSaving] = useState(false);

  const setF = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  // Load money accounts and remisiones once (needed by apply modals from any tab)
  useEffect(() => {
    api.getMoneyAccounts().then(setAccounts).catch(() => {});
    api.getRemisiones({ limit: 200 }).then(setRemisiones).catch(() => {});
  }, []);

  // Load data on tab change
  const loadTab = useCallback(
    async (t: Tab) => {
      setErr('');
      setLoading(true);
      try {
        if (t === 'remisiones') {
          const r = await api.getRemisiones({ limit: 100 });
          setRemisiones(r);
        } else if (t === 'pagos') {
          const d = await api.getDashboardData(200);
          setPayments(d.payments ?? []);
          setPaymentApplications(d.payment_applications ?? []);
        } else if (t === 'anticipos') {
          setAnticipos(await api.getAnticipos({ limit: 100 }));
        } else if (t === 'devoluciones') {
          setDevoluciones(await api.getDevoluciones({ limit: 100 }));
        } else if (t === 'clientes') {
          setRanking(await api.getClientRanking());
        } else if (t === 'corte') {
          setCutData(await api.getCashCutData(cutDate));
        } else if (t === 'conciliacion') {
          const f = concFilter;
          setConcData(await api.getConciliacionData({ date_from: f.date_from || undefined, date_to: f.date_to || undefined, account_id: f.account_id || undefined }));
        }
      } catch (e: any) {
        setErr(e.message ?? 'Error cargando datos');
      } finally {
        setLoading(false);
      }
    },
    [cutDate]
  );

  useEffect(() => {
    loadTab(tab);
  }, [tab, loadTab]);

  const reload = () => loadTab(tab);

  // ─── Modal handlers ─────────────────────────────────────────────────────────

  const openModal = (m: ModalState) => {
    setForm({});
    setFormErr('');
    setModal(m);
  };

  async function submitPago() {
    if (modal?.kind !== 'pago') return;
    const amount = parseFloat(form.amount || '0');
    if (!amount || !form.method) return setFormErr('Importe y método requeridos');
    setSaving(true);
    try {
      await api.createPayment({
        customer_name: modal.remision.customer_name_snapshot,
        sales_document_id: modal.remision.id,
        sales_folio: modal.remision.folio,
        payment_method: form.method,
        amount,
        destination_money_account_id: form.account_id || undefined,
        tracking_key: form.tracking_key || undefined,
        reference: form.reference || undefined,
        notes: form.notes || undefined,
      });
      setModal(null);
      reload();
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitApplyPago() {
    if (modal?.kind !== 'apply_pago') return;
    const amount = parseFloat(form.amount || '0');
    if (!amount || !form.sales_document_id) return setFormErr('Remisión e importe requeridos');
    setSaving(true);
    try {
      await api.applyPayment({ payment_id: modal.payment.id, sales_document_id: form.sales_document_id, amount_applied: amount });
      setModal(null);
      reload();
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitConfirmPago() {
    if (modal?.kind !== 'confirm_pago') return;
    setSaving(true);
    try {
      await api.confirmPayment({ payment_id: modal.payment.id, bank_reference: form.bank_reference || undefined });
      setModal(null);
      reload();
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitAnticipo() {
    const amount = parseFloat(form.amount || '0');
    if (!amount || !form.method || !form.customer) return setFormErr('Cliente, importe y método requeridos');
    setSaving(true);
    try {
      await api.createAnticipo({ customer_name: form.customer, amount, payment_method: form.method, destination_money_account_id: form.account_id || undefined });
      setModal(null);
      setAnticipos(await api.getAnticipos({ limit: 100 }));
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitApplyAnticipo() {
    if (modal?.kind !== 'apply_anticipo') return;
    const amount = parseFloat(form.amount || '0');
    if (!amount || !form.sales_document_id) return setFormErr('Remisión e importe requeridos');
    setSaving(true);
    try {
      await api.applyAnticipo({ anticipo_id: modal.anticipo.id, sales_document_id: form.sales_document_id, amount_applied: amount });
      setModal(null);
      reload();
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitDevolucion() {
    const amount = parseFloat(form.amount || '0');
    if (!amount || !form.customer) return setFormErr('Cliente e importe requeridos');
    setSaving(true);
    try {
      await api.createDevolucion({ customer_name: form.customer, sales_document_folio: form.sales_folio || undefined, amount, reason: form.reason || undefined });
      setModal(null);
      setDevoluciones(await api.getDevoluciones({ limit: 100 }));
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitResolveDevolucion() {
    if (modal?.kind !== 'resolve_dev') return;
    if (!form.resolution) return setFormErr('Selecciona tipo de resolución');
    if (form.resolution === 'abono_remision' && !form.sales_document_id) return setFormErr('Remisión requerida para abono');
    setSaving(true);
    try {
      await api.applyDevolucion({ devolucion_id: modal.devolucion.id, resolution: form.resolution as any, sales_document_id: form.sales_document_id || undefined });
      setModal(null);
      reload();
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function submitCloseCut() {
    if (modal?.kind !== 'close_corte') return;
    if (!form.account_id) return setFormErr('Cuenta destino requerida');
    setSaving(true);
    try {
      await api.closeCashCut({ cash_cut_id: modal.cut.id, destination_account_id: form.account_id, counted_amount: form.counted ? parseFloat(form.counted) : undefined });
      setModal(null);
      setCutData(await api.getCashCutData(cutDate));
    } catch (e: any) {
      setFormErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  // ─── Filter helpers ──────────────────────────────────────────────────────────

  const filteredRem = remisiones.filter((r) => {
    if (remFilter.customer && !r.customer_name_snapshot.toLowerCase().includes(remFilter.customer.toLowerCase())) return false;
    if (remFilter.status && r.status !== remFilter.status) return false;
    if (remFilter.date_from && r.document_date < remFilter.date_from) return false;
    if (remFilter.date_to && r.document_date > remFilter.date_to) return false;
    return true;
  });

  const filteredPay = payments.filter((p) => {
    if (payFilter.customer && !p.customer_name?.toLowerCase().includes(payFilter.customer.toLowerCase())) return false;
    if (payFilter.date_from && (p.payment_date ?? '') < payFilter.date_from) return false;
    if (payFilter.date_to && (p.payment_date ?? '') > payFilter.date_to) return false;
    if (payFilter.confirmation_status && p.confirmation_status !== payFilter.confirmation_status) return false;
    return true;
  });

  const filteredAnt = anticipos.filter((a) => {
    if (antFilter.customer && !a.customer_name?.toLowerCase().includes(antFilter.customer.toLowerCase())) return false;
    if (antFilter.status && a.status !== antFilter.status) return false;
    return true;
  });

  const filteredDev = devoluciones.filter((d) => {
    if (devFilter.customer && !d.customer_name?.toLowerCase().includes(devFilter.customer.toLowerCase())) return false;
    if (devFilter.status && d.status !== devFilter.status) return false;
    return true;
  });

  const loadProductSlot = (slotNum: 1 | 2, product_name: string) => {
    const setter = slotNum === 1 ? setSlot1 : setSlot2;
    setter((p) => ({ ...p, loading: true }));
    api.getClientProductMonth({ product_name })
      .then((d) => setter((p) => ({ ...p, loading: false, stats: { label: d.product_name, por_cliente: d.por_cliente } })))
      .catch((e) => { setErr(e.message); setter((p) => ({ ...p, loading: false })); });
  };

  const filteredClientes = (() => {
    const base = ranking?.clientes.filter((c) => {
      if (rankFilter === '8') return (c.dias_sin_comprar ?? 0) >= 8;
      if (rankFilter === '15') return (c.dias_sin_comprar ?? 0) >= 15;
      if (rankFilter === '21') return (c.dias_sin_comprar ?? 0) >= 21;
      return true;
    }) ?? [];
    const { col, dir } = rankSort;
    return [...base].sort((a, b) => {
      let av: number | string = 0;
      let bv: number | string = 0;
      if (col === 'dias_sin_comprar') { av = a.dias_sin_comprar ?? 9999; bv = b.dias_sin_comprar ?? 9999; }
      else if (col === 'm_actual') { av = a.m_actual; bv = b.m_actual; }
      else if (col === 'm1') { av = a.m1; bv = b.m1; }
      else if (col === 'm2') { av = a.m2; bv = b.m2; }
      else if (col === 'ultima_compra') { av = a.ultima_compra ?? ''; bv = b.ultima_compra ?? ''; }
      else if (col === 'ticket_promedio') { av = a.ticket_promedio; bv = b.ticket_promedio; }
      else if (col === 'producto1') { av = slot1.stats?.por_cliente[a.customer_name] ?? 0; bv = slot1.stats?.por_cliente[b.customer_name] ?? 0; }
      else if (col === 'producto2') { av = slot2.stats?.por_cliente[a.customer_name] ?? 0; bv = slot2.stats?.por_cliente[b.customer_name] ?? 0; }
      if (av < bv) return dir === 'asc' ? -1 : 1;
      if (av > bv) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  })();

  // Índice pago → remisiones aplicadas
  const appsMap = paymentApplications.reduce<Record<string, string[]>>((acc, a) => {
    if (a.payment_id && a.sales_folio) {
      if (!acc[a.payment_id]) acc[a.payment_id] = [];
      acc[a.payment_id].push(a.sales_folio);
    }
    return acc;
  }, {});

  // Nombres de clientes de remisiones para autocompletado
  const customerNames = Array.from(new Set(remisiones.map((r) => r.customer_name_snapshot).filter(Boolean) as string[])).sort();

  // ─── Remision picker for apply modals ────────────────────────────────────────
  const RemisionSelect = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Seleccionar remisión...</option>
      {remisiones
        .filter((r) => r.status !== 'cancelada' && r.status !== 'pagada' && (r.balance_total ?? r.total) > 0)
        .map((r) => (
          <option key={r.id} value={r.id}>
            {r.folio} — {r.customer_name_snapshot} — Saldo: {fmt(r.balance_total ?? r.total)}
          </option>
        ))}
    </select>
  );

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Autocompletado de clientes — disponible en todos los inputs con list="billing-customers" */}
      <datalist id="billing-customers">
        {customerNames.map((n) => <option key={n} value={n} />)}
      </datalist>

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Cobranza</h1>
          <p className="text-xs text-gray-500">{projectContext.company_label} · {projectContext.project_label}</p>
        </div>
        <button onClick={reload} className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-blue-600">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Actualizar
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6 overflow-x-auto">
        <div className="flex gap-0 min-w-max">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                ${tab === id ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {err && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {err}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <Loader2 size={32} className="animate-spin text-blue-500" />
        </div>
      )}

      {/* ── Tab: Remisiones ── */}
      {!loading && tab === 'remisiones' && (
        <div className="p-6">
          <div className="flex flex-wrap gap-2 mb-4">
            <input placeholder="Cliente..." className={`${inputCls} w-48`} list="billing-customers" value={remFilter.customer} onChange={(e) => setRemFilter((p) => ({ ...p, customer: e.target.value }))} />
            <select className={`${inputCls} w-40`} value={remFilter.status} onChange={(e) => setRemFilter((p) => ({ ...p, status: e.target.value }))}>
              <option value="">Todos los estados</option>
              <option value="emitida">Emitida</option>
              <option value="pendiente">Pendiente</option>
              <option value="parcial">Parcial</option>
              <option value="pagada">Pagada</option>
              <option value="cancelada">Cancelada</option>
            </select>
            <input type="date" className={`${inputCls} w-40`} value={remFilter.date_from} onChange={(e) => setRemFilter((p) => ({ ...p, date_from: e.target.value }))} />
            <input type="date" className={`${inputCls} w-40`} value={remFilter.date_to} onChange={(e) => setRemFilter((p) => ({ ...p, date_to: e.target.value }))} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs">
                <tr>
                  <th className="text-left px-4 py-3">Folio</th>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Cliente</th>
                  <th className="text-right px-4 py-3">Total</th>
                  <th className="text-right px-4 py-3">Cobrado</th>
                  <th className="text-right px-4 py-3">Saldo</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {filteredRem.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-10 text-gray-400">Sin registros</td></tr>
                )}
                {filteredRem.map((r) => (
                  <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-blue-700">{r.folio}</td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(r.document_date)}</td>
                    <td className="px-4 py-3">{r.customer_name_snapshot}</td>
                    <td className="px-4 py-3 text-right">{fmt(r.total)}</td>
                    <td className="px-4 py-3 text-right text-green-700">{fmt(r.paid_total)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-red-600">{fmt(r.balance_total ?? r.total - (r.paid_total ?? 0))}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => api.getRemisionHtml(r.folio).then(api.openHtml)} title="Imprimir" className="text-gray-400 hover:text-blue-600"><Printer size={14} /></button>
                        {r.status !== 'cancelada' && r.status !== 'pagada' && (
                          <button onClick={() => { setRemisiones((prev) => prev); openModal({ kind: 'pago', remision: r }); }} className="text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700">
                            Cobrar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Pagos ── */}
      {!loading && tab === 'pagos' && (
        <div className="p-6">
          <div className="flex flex-wrap gap-2 mb-4">
            <input placeholder="Cliente..." className={`${inputCls} w-48`} list="billing-customers" value={payFilter.customer} onChange={(e) => setPayFilter((p) => ({ ...p, customer: e.target.value }))} />
            <input type="date" className={`${inputCls} w-40`} value={payFilter.date_from} onChange={(e) => setPayFilter((p) => ({ ...p, date_from: e.target.value }))} />
            <input type="date" className={`${inputCls} w-40`} value={payFilter.date_to} onChange={(e) => setPayFilter((p) => ({ ...p, date_to: e.target.value }))} />
            <select className={`${inputCls} w-44`} value={payFilter.confirmation_status} onChange={(e) => setPayFilter((p) => ({ ...p, confirmation_status: e.target.value }))}>
              <option value="">Todos los estados</option>
              <option value="confirmado">Confirmado</option>
              <option value="por_confirmar">Por confirmar</option>
            </select>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs">
                <tr>
                  <th className="text-left px-4 py-3">Folio</th>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Cliente</th>
                  <th className="text-left px-4 py-3">Método</th>
                  <th className="text-right px-4 py-3">Importe</th>
                  <th className="text-right px-4 py-3">Sin aplicar</th>
                  <th className="text-left px-4 py-3">Remisión</th>
                  <th className="text-center px-4 py-3">Confirmación</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {filteredPay.length === 0 && (
                  <tr><td colSpan={9} className="text-center py-10 text-gray-400">Sin registros</td></tr>
                )}
                {filteredPay.map((p) => (
                  <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-blue-700">{p.folio}</td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(p.payment_date)}</td>
                    <td className="px-4 py-3">{p.customer_name}</td>
                    <td className="px-4 py-3">{METODO_LABEL[p.payment_method] ?? p.payment_method}</td>
                    <td className="px-4 py-3 text-right font-semibold">{fmt(p.amount)}</td>
                    <td className="px-4 py-3 text-right text-orange-600">{fmt(p.unapplied_amount)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{(appsMap[p.id] ?? []).join(', ') || '—'}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={p.confirmation_status ?? 'confirmado'} /></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2 justify-end">
                        {p.confirmation_status === 'por_confirmar' && (
                          <button onClick={() => openModal({ kind: 'confirm_pago', payment: p })} className="text-xs bg-green-600 text-white rounded px-2 py-1 hover:bg-green-700">
                            Confirmar
                          </button>
                        )}
                        {(p.unapplied_amount ?? 0) > 0 && (
                          <button onClick={() => openModal({ kind: 'apply_pago', payment: p })} className="text-xs border border-blue-600 text-blue-600 rounded px-2 py-1 hover:bg-blue-50">
                            Aplicar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Anticipos ── */}
      {!loading && tab === 'anticipos' && (
        <div className="p-6">
          <div className="flex flex-wrap gap-2 mb-4 items-center">
            <input placeholder="Cliente..." className={`${inputCls} w-48`} value={antFilter.customer} onChange={(e) => setAntFilter((p) => ({ ...p, customer: e.target.value }))} />
            <select className={`${inputCls} w-40`} value={antFilter.status} onChange={(e) => setAntFilter((p) => ({ ...p, status: e.target.value }))}>
              <option value="">Todos</option>
              <option value="disponible">Disponible</option>
              <option value="parcial">Parcial</option>
              <option value="aplicado">Aplicado</option>
            </select>
            <button onClick={() => openModal({ kind: 'nuevo_anticipo' })} className={`${btnPrimary} flex items-center gap-1 ml-auto`}>
              <Plus size={14} /> Nuevo Anticipo
            </button>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs">
                <tr>
                  <th className="text-left px-4 py-3">Folio</th>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Cliente</th>
                  <th className="text-left px-4 py-3">Método</th>
                  <th className="text-right px-4 py-3">Importe</th>
                  <th className="text-right px-4 py-3">Disponible</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {filteredAnt.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-10 text-gray-400">Sin anticipos</td></tr>
                )}
                {filteredAnt.map((a) => (
                  <tr key={a.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-indigo-700">{a.folio}</td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(a.payment_date)}</td>
                    <td className="px-4 py-3">{a.customer_name}</td>
                    <td className="px-4 py-3">{METODO_LABEL[a.payment_method] ?? a.payment_method}</td>
                    <td className="px-4 py-3 text-right">{fmt(a.amount)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-blue-700">{fmt(a.unapplied_amount)}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {a.status !== 'aplicado' && (a.unapplied_amount ?? 0) > 0 && (
                        <button onClick={() => openModal({ kind: 'apply_anticipo', anticipo: a })} className="text-xs border border-blue-600 text-blue-600 rounded px-2 py-1 hover:bg-blue-50">
                          Aplicar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Devoluciones ── */}
      {!loading && tab === 'devoluciones' && (
        <div className="p-6">
          <div className="flex flex-wrap gap-2 mb-4 items-center">
            <input placeholder="Cliente..." className={`${inputCls} w-48`} value={devFilter.customer} onChange={(e) => setDevFilter((p) => ({ ...p, customer: e.target.value }))} />
            <select className={`${inputCls} w-40`} value={devFilter.status} onChange={(e) => setDevFilter((p) => ({ ...p, status: e.target.value }))}>
              <option value="">Todos</option>
              <option value="pendiente">Pendiente</option>
              <option value="aprobada">Aprobada</option>
              <option value="aplicada">Aplicada</option>
            </select>
            <button onClick={() => openModal({ kind: 'nueva_dev' })} className={`${btnPrimary} flex items-center gap-1 ml-auto`}>
              <Plus size={14} /> Nueva Devolución
            </button>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs">
                <tr>
                  <th className="text-left px-4 py-3">Folio</th>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Cliente</th>
                  <th className="text-left px-4 py-3">Ref. Remisión</th>
                  <th className="text-right px-4 py-3">Importe</th>
                  <th className="text-left px-4 py-3">Motivo</th>
                  <th className="text-center px-4 py-3">Estado</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {filteredDev.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-10 text-gray-400">Sin devoluciones</td></tr>
                )}
                {filteredDev.map((d) => (
                  <tr key={d.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-rose-700">{d.folio}</td>
                    <td className="px-4 py-3 text-gray-600">{fmtDate(d.created_at)}</td>
                    <td className="px-4 py-3">{d.customer_name}</td>
                    <td className="px-4 py-3 font-mono text-gray-500">{d.sales_document_folio ?? '-'}</td>
                    <td className="px-4 py-3 text-right">{fmt(d.amount)}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{d.reason ?? '-'}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={d.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {d.status === 'aprobada' && (
                        <button onClick={() => openModal({ kind: 'resolve_dev', devolucion: d })} className="text-xs bg-indigo-600 text-white rounded px-2 py-1 hover:bg-indigo-700">
                          Resolver
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Estado de Cuenta ── */}
      {!loading && tab === 'estado_cuenta' && (
        <div className="p-6 max-w-5xl">
          <div className="flex gap-2 mb-6">
            <input
              placeholder="Seleccionar o escribir cliente..."
              className={`${inputCls} flex-1`}
              list="billing-customers"
              value={stmtQuery}
              onChange={(e) => setStmtQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && stmtQuery) api.getClientStatement(stmtQuery).then(setStatement).catch((e) => setErr(e.message)); }}
            />
            <button
              onClick={() => stmtQuery && api.getClientStatement(stmtQuery).then(setStatement).catch((e) => setErr(e.message))}
              className={`${btnPrimary} flex items-center gap-1`}
            >
              <Search size={14} /> Buscar
            </button>
          </div>

          {statement && (
            <>
              <h2 className="text-lg font-bold text-gray-900 mb-4">{statement.customer_name}</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
                <KpiCard label="Total Facturado" value={fmt(statement.kpis.total_facturado)} />
                <KpiCard label="Total Cobrado" value={fmt(statement.kpis.total_cobrado)} />
                <KpiCard label="Saldo Remisiones" value={fmt(statement.kpis.saldo_pendiente)} />
                {(statement.kpis.saldo_pedidos ?? 0) > 0 && (
                  <KpiCard label="Saldo Pedidos" value={fmt(statement.kpis.saldo_pedidos)} sub="órdenes sin remisionar" />
                )}
                <KpiCard label="Anticipos Disponibles" value={fmt(statement.kpis.anticipos_disponibles)} />
                <KpiCard label="Último Pago" value={fmtDate(statement.kpis.ultimo_pago)} sub={statement.kpis.dias_sin_pagar != null ? `${statement.kpis.dias_sin_pagar} días` : undefined} />
                <KpiCard label="Última Compra" value={fmtDate(statement.kpis.ultima_compra)} sub={statement.kpis.dias_sin_comprar != null ? `${statement.kpis.dias_sin_comprar} días` : undefined} />
                <KpiCard label="Ticket Promedio" value={fmt(statement.kpis.ticket_promedio)} />
                <KpiCard label="Pago Prom/Mes" value={fmt(statement.kpis.pago_promedio_mes)} sub={statement.kpis.frecuencia_compra_dias != null ? `Frecuencia: ${statement.kpis.frecuencia_compra_dias}d` : undefined} />
              </div>

              <h3 className="font-semibold text-gray-800 mb-2">Kardex</h3>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 text-xs">
                    <tr>
                      <th className="text-left px-4 py-3">Fecha</th>
                      <th className="text-left px-4 py-3">Tipo</th>
                      <th className="text-left px-4 py-3">Folio</th>
                      <th className="text-left px-4 py-3">Concepto</th>
                      <th className="text-right px-4 py-3 text-blue-600">Importe Pedido</th>
                      <th className="text-right px-4 py-3">Cargo</th>
                      <th className="text-right px-4 py-3">Abono</th>
                      <th className="text-right px-4 py-3">Saldo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statement.kardex.map((k, i) => (
                      <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-600">{fmtDate(k.fecha)}</td>
                        <td className="px-4 py-2">
                          {k.tipo === 'Pedido'
                            ? <span className="text-xs bg-blue-50 text-blue-600 rounded px-2 py-0.5">{k.tipo} (ref)</span>
                            : <span className="text-xs bg-gray-100 rounded px-2 py-0.5">{k.tipo}</span>}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs text-gray-500">{k.folio}</td>
                        <td className="px-4 py-2">{k.concepto}</td>
                        <td className="px-4 py-2 text-right text-blue-600">{k.monto_ref ? fmt(k.monto_ref) : ''}</td>
                        <td className="px-4 py-2 text-right text-red-600">{k.cargo ? fmt(k.cargo) : ''}</td>
                        <td className="px-4 py-2 text-right text-green-700">{k.abono ? fmt(k.abono) : ''}</td>
                        <td className={`px-4 py-2 text-right font-semibold ${k.saldo > 0 ? 'text-red-600' : 'text-gray-900'}`}>{fmt(k.saldo)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab: Clientes ── */}
      {!loading && tab === 'clientes' && ranking && (
        <div className="p-6">
          {/* Totales */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            <KpiCard label={`Mes actual (${ranking.meses.m_actual})`} value={fmt(ranking.totales.m_actual)} />
            <KpiCard label={`M-1 (${ranking.meses.m1})`} value={fmt(ranking.totales.m1)} />
            <KpiCard label={`M-2 (${ranking.meses.m2})`} value={fmt(ranking.totales.m2)} />
            <KpiCard label="Proyección" value={fmt(ranking.totales.proyeccion)} sub={`${ranking.totales.tendencia_pct >= 0 ? '+' : ''}${ranking.totales.tendencia_pct}% vs M-2`} />
          </div>

          {/* Columnas de producto */}
          <div className="flex flex-col gap-2 mb-4">
            {/* Slot 1 */}
            <div className="flex gap-2 items-center">
              <span className="text-xs text-gray-400 w-16 shrink-0">Col. 1:</span>
              <input
                placeholder="Producto (ej. varilla 3/8)..."
                className={`${inputCls} flex-1 max-w-sm`}
                value={slot1.input}
                onChange={(e) => setSlot1((p) => ({ ...p, input: e.target.value }))}
                onKeyDown={(e) => { if (e.key === 'Enter' && slot1.input.trim()) loadProductSlot(1, slot1.input.trim()); }}
              />
              <button className={btnPrimary} disabled={slot1.loading || !slot1.input.trim()} onClick={() => loadProductSlot(1, slot1.input.trim())}>
                {slot1.loading ? 'Cargando...' : 'Ver'}
              </button>
              {slot1.stats && <button className={btnSecondary} onClick={() => setSlot1((p) => ({ ...p, stats: null, input: '' }))}>Quitar</button>}
            </div>
            {/* Slot 2 */}
            <div className="flex gap-2 items-center">
              <span className="text-xs text-gray-400 w-16 shrink-0">Col. 2:</span>
              <input
                placeholder="Producto 2..."
                className={`${inputCls} flex-1 max-w-sm`}
                value={slot2.input}
                onChange={(e) => setSlot2((p) => ({ ...p, input: e.target.value }))}
                onKeyDown={(e) => { if (e.key === 'Enter' && slot2.input.trim()) loadProductSlot(2, slot2.input.trim()); }}
              />
              <button className={btnPrimary} disabled={slot2.loading || !slot2.input.trim()} onClick={() => loadProductSlot(2, slot2.input.trim())}>
                {slot2.loading ? 'Cargando...' : 'Ver'}
              </button>
              {slot2.stats && <button className={btnSecondary} onClick={() => setSlot2((p) => ({ ...p, stats: null, input: '' }))}>Quitar</button>}
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mb-4">
            {([['todos', 'Todos'], ['8', '+8 días'], ['15', '+15 días'], ['21', '+21 días']] as const).map(([v, label]) => (
              <button key={v} onClick={() => setRankFilter(v)} className={`px-3 py-1.5 rounded-full text-sm ${rankFilter === v ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                {label}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs">
                <tr>
                  <th className="text-center px-3 py-3">#</th>
                  <th className="text-center px-3 py-3" />
                  <th className="text-left px-3 py-3">Cliente</th>
                  <SortTh col="dias_sin_comprar" sort={rankSort} onSort={setRankSort} align="center">Sin comprar</SortTh>
                  <SortTh col="m_actual" sort={rankSort} onSort={setRankSort} align="right">Mes actual</SortTh>
                  <SortTh col="m1" sort={rankSort} onSort={setRankSort} align="right">M-1</SortTh>
                  <SortTh col="m2" sort={rankSort} onSort={setRankSort} align="right">M-2</SortTh>
                  <SortTh col="ultima_compra" sort={rankSort} onSort={setRankSort} align="center">Última compra</SortTh>
                  {slot1.stats && <SortTh col="producto1" sort={rankSort} onSort={setRankSort} align="right" className="text-blue-700">{slot1.stats.label}</SortTh>}
                  {slot2.stats && <SortTh col="producto2" sort={rankSort} onSort={setRankSort} align="right" className="text-purple-700">{slot2.stats.label}</SortTh>}
                  <SortTh col="ticket_promedio" sort={rankSort} onSort={setRankSort} align="right">Ticket Prom.</SortTh>
                </tr>
              </thead>
              <tbody>
                {filteredClientes.length === 0 && (
                  <tr><td colSpan={9 + (slot1.stats ? 1 : 0) + (slot2.stats ? 1 : 0)} className="text-center py-10 text-gray-400">Sin datos</td></tr>
                )}
                {filteredClientes.map((c, i) => (
                  <tr key={c.customer_key} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-3 py-2.5 text-center text-gray-400">{i + 1}</td>
                    <td className="px-3 py-2.5 text-center"><Semaforo semaforo={c.semaforo} /></td>
                    <td className="px-3 py-2.5 font-medium">{c.customer_name}</td>
                    <td className="px-3 py-2.5 text-center text-gray-600">{c.dias_sin_comprar != null ? `${c.dias_sin_comprar}d` : '-'}</td>
                    <td className="px-3 py-2.5 text-right font-semibold text-blue-700">{c.m_actual > 0 ? fmt(c.m_actual) : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-2.5 text-right">{c.m1 > 0 ? fmt(c.m1) : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-2.5 text-right">{c.m2 > 0 ? fmt(c.m2) : <span className="text-gray-300">—</span>}</td>
                    <td className="px-3 py-2.5 text-center text-gray-500 text-xs">{c.ultima_compra ? fmtDate(c.ultima_compra) : '—'}</td>
                    {slot1.stats && (
                      <td className="px-3 py-2.5 text-right text-blue-700 font-medium">
                        {slot1.stats.por_cliente[c.customer_name] ? fmt(slot1.stats.por_cliente[c.customer_name]) : <span className="text-gray-300">—</span>}
                      </td>
                    )}
                    {slot2.stats && (
                      <td className="px-3 py-2.5 text-right text-purple-700 font-medium">
                        {slot2.stats.por_cliente[c.customer_name] ? fmt(slot2.stats.por_cliente[c.customer_name]) : <span className="text-gray-300">—</span>}
                      </td>
                    )}
                    <td className="px-3 py-2.5 text-right text-gray-600">{c.ticket_promedio > 0 ? fmt(c.ticket_promedio) : <span className="text-gray-300">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Corte de Caja ── */}
      {!loading && tab === 'corte' && (
        <div className="p-6 space-y-6 max-w-5xl">
          {/* Date selector */}
          <div className="flex gap-3 items-center">
            <input
              type="date"
              className={`${inputCls} w-44`}
              value={cutDate}
              onChange={(e) => setCutDate(e.target.value)}
            />
            <button onClick={() => api.getCashCutData(cutDate).then(setCutData).catch((e) => setErr(e.message))} className={btnPrimary}>Cargar</button>
            <button
              onClick={() => api.openCashCut({}).then(() => api.getCashCutData(cutDate).then(setCutData)).catch((e) => setErr(e.message))}
              className={`${btnSecondary} ml-auto flex items-center gap-1`}
            >
              <Plus size={14} /> Abrir corte
            </button>
          </div>

          {cutData && (
            <>
              {/* Totales de hoy */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <KpiCard label="Ventas del día" value={fmt(cutData.totales.total_ventas_dia)} />
                <KpiCard label="Cobrado hoy" value={fmt(cutData.totales.total_pagos_hoy)} />
                <KpiCard label="CXC del día" value={fmt(cutData.totales.cxc_dia)} />
                <KpiCard label="CXC anteriores" value={fmt(cutData.totales.total_cxc_anteriores)} />
              </div>

              {/* Ventas del día */}
              <Section title={`Remisiones del día (${cutData.ventas_dia.length})`}>
                <SimpleTable
                  cols={['Folio', 'Cliente', 'Total', 'Cobrado', 'Saldo', 'Estado']}
                  rows={cutData.ventas_dia.map((r) => [r.folio, r.customer_name_snapshot, fmt(r.total), fmt(r.paid_total), fmt(r.balance_total ?? r.total - (r.paid_total ?? 0)), <StatusBadge key="s" status={r.status} />])}
                />
              </Section>

              {/* Pagos de hoy */}
              <Section title={`Pagos recibidos hoy (${cutData.pagos_hoy.length})`}>
                <SimpleTable
                  cols={['Folio', 'Cliente', 'Método', 'Importe', 'Confirmación']}
                  rows={cutData.pagos_hoy.map((p) => [p.folio, p.customer_name ?? '-', METODO_LABEL[p.payment_method] ?? p.payment_method, fmt(p.amount), <StatusBadge key="s" status={p.confirmation_status ?? 'confirmado'} />])}
                />
              </Section>

              {/* CXC anteriores */}
              {cutData.cxc_anteriores.length > 0 && (
                <Section title={`Recordatorio CXC (${cutData.cxc_anteriores.length} pendientes)`} highlight>
                  <SimpleTable
                    cols={['Folio', 'Fecha', 'Cliente', 'Saldo', 'Días']}
                    rows={cutData.cxc_anteriores.map((r) => [r.folio, fmtDate(r.document_date), r.customer_name_snapshot, fmt(r.balance_total ?? r.total), `${r.dias_vencido ?? 0}d`])}
                  />
                </Section>
              )}

              {/* Por confirmar */}
              {cutData.por_confirmar.length > 0 && (
                <Section title={`Transferencias por confirmar (${cutData.por_confirmar.length})`} highlight>
                  <SimpleTable
                    cols={['Folio', 'Fecha', 'Cliente', 'Método', 'Importe', 'Espera']}
                    rows={cutData.por_confirmar.map((p) => [p.folio, fmtDate(p.payment_date), p.customer_name ?? '-', METODO_LABEL[p.payment_method] ?? p.payment_method, fmt(p.amount), `${p.dias_esperando ?? 0}d`])}
                  />
                </Section>
              )}

              {/* Cortes abiertos */}
              {cutData.cortes_abiertos.length > 0 && (
                <Section title={`Cortes abiertos (${cutData.cortes_abiertos.length})`}>
                  <div className="space-y-2">
                    {cutData.cortes_abiertos.map((c) => (
                      <div key={c.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                        <div>
                          <span className="font-mono text-sm text-gray-700">{c.folio ?? c.id.slice(0, 8)}</span>
                          <span className="text-xs text-gray-500 ml-3">{fmtDate(c.cut_date)}</span>
                          {c.responsible_user && <span className="text-xs text-gray-500 ml-2">· {c.responsible_user}</span>}
                        </div>
                        <button onClick={() => openModal({ kind: 'close_corte', cut: c })} className="text-xs bg-gray-800 text-white rounded px-3 py-1 hover:bg-black">
                          Cerrar corte
                        </button>
                      </div>
                    ))}
                  </div>
                </Section>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab: Conciliación ── */}
      {!loading && tab === 'conciliacion' && (
        <div className="p-6 space-y-6 max-w-6xl">
          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-end">
            <div>
              <p className="text-xs text-gray-500 mb-1">Desde</p>
              <input type="date" className={`${inputCls} w-40`} value={concFilter.date_from} onChange={(e) => setConcFilter((p) => ({ ...p, date_from: e.target.value }))} />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Hasta</p>
              <input type="date" className={`${inputCls} w-40`} value={concFilter.date_to} onChange={(e) => setConcFilter((p) => ({ ...p, date_to: e.target.value }))} />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Cuenta bancaria</p>
              <select className={`${inputCls} w-52`} value={concFilter.account_id} onChange={(e) => setConcFilter((p) => ({ ...p, account_id: e.target.value }))}>
                <option value="">Todas las cuentas</option>
                {accounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
              </select>
            </div>
            <button
              onClick={() => api.getConciliacionData({ date_from: concFilter.date_from || undefined, date_to: concFilter.date_to || undefined, account_id: concFilter.account_id || undefined }).then(setConcData).catch((e) => setErr(e.message))}
              className={`${btnPrimary} flex items-center gap-1`}
            >
              <Search size={14} /> Conciliar
            </button>
            <button
              onClick={() => api.ensureConciliacionTable().catch((e) => setErr(e.message))}
              className={`${btnSecondary} text-xs ml-auto`}
              title="Crear tabla de cruces si no existe"
            >
              Inicializar tabla
            </button>
          </div>

          {/* Stats */}
          {concData && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-green-700">{concData.stats.total_matched}</p>
                  <p className="text-xs text-green-600 mt-1">Cruzados</p>
                  <p className="text-sm font-semibold text-green-700">{fmt(concData.stats.importe_matched)}</p>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-yellow-700">{concData.stats.total_solo_banco}</p>
                  <p className="text-xs text-yellow-600 mt-1">Solo en banco</p>
                  <p className="text-sm font-semibold text-yellow-700">{fmt(concData.stats.importe_solo_banco)}</p>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-red-700">{concData.stats.total_solo_billing}</p>
                  <p className="text-xs text-red-600 mt-1">Solo en cobranza</p>
                  <p className="text-sm font-semibold text-red-700">{fmt(concData.stats.importe_solo_billing)}</p>
                </div>
              </div>

              {/* Matched */}
              {concData.matched.length > 0 && (
                <Section title={`✓ Cruzados automáticamente (${concData.matched.length})`}>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs">
                      <tr>
                        <th className="text-left px-4 py-2">Mov. Banco</th>
                        <th className="text-left px-4 py-2">Fecha Banco</th>
                        <th className="text-left px-4 py-2">Folio Pago</th>
                        <th className="text-left px-4 py-2">Cliente</th>
                        <th className="text-right px-4 py-2">Importe</th>
                        <th className="text-center px-4 py-2">Tipo cruce</th>
                      </tr>
                    </thead>
                    <tbody>
                      {concData.matched.map((row) => (
                        <tr key={row.id} className="border-t border-gray-100 hover:bg-green-50">
                          <td className="px-4 py-2 font-mono text-xs text-gray-500">{row.folio}</td>
                          <td className="px-4 py-2 text-gray-600">{fmtDate(row.movement_date)}</td>
                          <td className="px-4 py-2 font-mono text-blue-700">{row.payment?.folio ?? row.source_folio ?? '-'}</td>
                          <td className="px-4 py-2">{row.payment?.customer_name ?? '-'}</td>
                          <td className="px-4 py-2 text-right font-semibold text-green-700">{fmt(row.amount)}</td>
                          <td className="px-4 py-2 text-center">
                            <span className="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5">{row.match_type?.replace('auto_', '') ?? 'manual'}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Section>
              )}

              {/* Solo banco */}
              {concData.solo_banco.length > 0 && (
                <Section title={`⚠ Solo en banco — sin pago en cobranza (${concData.solo_banco.length})`} highlight>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs">
                      <tr>
                        <th className="text-left px-4 py-2">Mov. Banco</th>
                        <th className="text-left px-4 py-2">Fecha</th>
                        <th className="text-left px-4 py-2">Clave rastreo</th>
                        <th className="text-right px-4 py-2">Importe</th>
                        <th className="text-center px-4 py-2">Banco</th>
                        <th className="px-4 py-2" />
                      </tr>
                    </thead>
                    <tbody>
                      {concData.solo_banco.map((row) => (
                        <tr key={row.id} className="border-t border-gray-100 hover:bg-yellow-50">
                          <td className="px-4 py-2 font-mono text-xs text-gray-500">{row.folio}</td>
                          <td className="px-4 py-2 text-gray-600">{fmtDate(row.movement_date)}</td>
                          <td className="px-4 py-2 font-mono text-xs text-gray-500">{row.clave_rastreo ?? '-'}</td>
                          <td className="px-4 py-2 text-right font-semibold">{fmt(row.amount)}</td>
                          <td className="px-4 py-2 text-center text-xs text-gray-500">{row.account_folio ?? '-'}</td>
                          <td className="px-4 py-2 text-right">
                            <button
                              onClick={() => { setMatchModal(row); setMatchPayId(''); }}
                              className="text-xs bg-yellow-600 text-white rounded px-2 py-1 hover:bg-yellow-700"
                            >
                              Cruzar manualmente
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Section>
              )}

              {/* Solo billing */}
              {concData.solo_billing.length > 0 && (
                <Section title={`✗ Solo en cobranza — sin movimiento bancario (${concData.solo_billing.length})`}>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs">
                      <tr>
                        <th className="text-left px-4 py-2">Folio Pago</th>
                        <th className="text-left px-4 py-2">Fecha</th>
                        <th className="text-left px-4 py-2">Cliente</th>
                        <th className="text-left px-4 py-2">Método</th>
                        <th className="text-right px-4 py-2">Importe</th>
                        <th className="text-center px-4 py-2">Confirmación</th>
                      </tr>
                    </thead>
                    <tbody>
                      {concData.solo_billing.map((p) => (
                        <tr key={p.id} className="border-t border-gray-100 hover:bg-red-50">
                          <td className="px-4 py-2 font-mono text-blue-700">{p.folio}</td>
                          <td className="px-4 py-2 text-gray-600">{fmtDate(p.payment_date)}</td>
                          <td className="px-4 py-2">{p.customer_name}</td>
                          <td className="px-4 py-2">{METODO_LABEL[p.payment_method] ?? p.payment_method}</td>
                          <td className="px-4 py-2 text-right font-semibold">{fmt(p.amount)}</td>
                          <td className="px-4 py-2 text-center"><StatusBadge status={p.confirmation_status ?? 'confirmado'} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Section>
              )}
            </>
          )}

          {!concData && (
            <div className="text-center py-16 text-gray-400">
              <GitCompare size={40} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Selecciona rango de fechas y presiona Conciliar</p>
            </div>
          )}
        </div>
      )}

      {/* ─── MODALS ─── */}

      {/* Registrar Pago */}
      {modal?.kind === 'pago' && (
        <Modal title={`Registrar pago — ${modal.remision.folio}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">
            Cliente: <strong>{modal.remision.customer_name_snapshot}</strong> · Saldo: <strong className="text-red-600">{fmt(modal.remision.balance_total ?? modal.remision.total)}</strong>
          </p>
          <Field label="Importe">
            <input type="number" className={inputCls} placeholder="0.00" value={form.amount ?? ''} onChange={(e) => setF('amount', e.target.value)} />
          </Field>
          <Field label="Método de pago">
            <select className={inputCls} value={form.method ?? ''} onChange={(e) => setF('method', e.target.value)}>
              <option value="">Seleccionar...</option>
              {METODOS.map((m) => <option key={m} value={m}>{METODO_LABEL[m]}</option>)}
            </select>
          </Field>
          {['transferencia', 'deposito'].includes(form.method ?? '') && (
            <Field label="Clave de rastreo / referencia">
              <input className={inputCls} value={form.tracking_key ?? ''} onChange={(e) => setF('tracking_key', e.target.value)} />
            </Field>
          )}
          <Field label="Cuenta destino (opcional)">
            <select className={inputCls} value={form.account_id ?? ''} onChange={(e) => setF('account_id', e.target.value)}>
              <option value="">Sin especificar</option>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
            </select>
          </Field>
          <Field label="Notas">
            <input className={inputCls} value={form.notes ?? ''} onChange={(e) => setF('notes', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitPago}>{saving ? 'Guardando...' : 'Registrar Pago'}</button>
          </div>
        </Modal>
      )}

      {/* Confirmar Pago */}
      {modal?.kind === 'confirm_pago' && (
        <Modal title={`Confirmar pago — ${modal.payment.folio}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">
            {modal.payment.customer_name} · {fmt(modal.payment.amount)} · {METODO_LABEL[modal.payment.payment_method] ?? modal.payment.payment_method}
          </p>
          <Field label="Referencia bancaria (opcional)">
            <input className={inputCls} placeholder="Folio de transferencia, número de depósito..." value={form.bank_reference ?? ''} onChange={(e) => setF('bank_reference', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={`${btnPrimary} bg-green-600 hover:bg-green-700`} disabled={saving} onClick={submitConfirmPago}>{saving ? 'Confirmando...' : 'Confirmar'}</button>
          </div>
        </Modal>
      )}

      {/* Aplicar Pago */}
      {modal?.kind === 'apply_pago' && (
        <Modal title={`Aplicar pago — ${modal.payment.folio}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">Disponible para aplicar: <strong>{fmt(modal.payment.unapplied_amount)}</strong></p>
          <Field label="Remisión">
            <RemisionSelect value={form.sales_document_id ?? ''} onChange={(v) => setF('sales_document_id', v)} />
          </Field>
          <Field label="Importe a aplicar">
            <input type="number" className={inputCls} value={form.amount ?? ''} onChange={(e) => setF('amount', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitApplyPago}>{saving ? 'Aplicando...' : 'Aplicar'}</button>
          </div>
        </Modal>
      )}

      {/* Nuevo Anticipo */}
      {modal?.kind === 'nuevo_anticipo' && (
        <Modal title="Nuevo Anticipo" onClose={() => setModal(null)}>
          <Field label="Cliente">
            <input className={inputCls} list="billing-customers" placeholder="Seleccionar cliente..." value={form.customer ?? ''} onChange={(e) => setF('customer', e.target.value)} />
          </Field>
          <Field label="Importe">
            <input type="number" className={inputCls} placeholder="0.00" value={form.amount ?? ''} onChange={(e) => setF('amount', e.target.value)} />
          </Field>
          <Field label="Método de pago">
            <select className={inputCls} value={form.method ?? ''} onChange={(e) => setF('method', e.target.value)}>
              <option value="">Seleccionar...</option>
              {METODOS.map((m) => <option key={m} value={m}>{METODO_LABEL[m]}</option>)}
            </select>
          </Field>
          <Field label="Cuenta destino (opcional)">
            <select className={inputCls} value={form.account_id ?? ''} onChange={(e) => setF('account_id', e.target.value)}>
              <option value="">Sin especificar</option>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
            </select>
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitAnticipo}>{saving ? 'Guardando...' : 'Crear Anticipo'}</button>
          </div>
        </Modal>
      )}

      {/* Aplicar Anticipo */}
      {modal?.kind === 'apply_anticipo' && (
        <Modal title={`Aplicar anticipo — ${modal.anticipo.folio}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">Disponible: <strong>{fmt(modal.anticipo.unapplied_amount)}</strong></p>
          <Field label="Remisión">
            <RemisionSelect value={form.sales_document_id ?? ''} onChange={(v) => setF('sales_document_id', v)} />
          </Field>
          <Field label="Importe a aplicar">
            <input type="number" className={inputCls} value={form.amount ?? ''} onChange={(e) => setF('amount', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitApplyAnticipo}>{saving ? 'Aplicando...' : 'Aplicar'}</button>
          </div>
        </Modal>
      )}

      {/* Nueva Devolución */}
      {modal?.kind === 'nueva_dev' && (
        <Modal title="Nueva Devolución" onClose={() => setModal(null)}>
          <Field label="Cliente">
            <input className={inputCls} list="billing-customers" placeholder="Seleccionar cliente..." value={form.customer ?? ''} onChange={(e) => setF('customer', e.target.value)} />
          </Field>
          <Field label="Folio de remisión (opcional)">
            <input className={inputCls} placeholder="REM-00001" value={form.sales_folio ?? ''} onChange={(e) => setF('sales_folio', e.target.value)} />
          </Field>
          <Field label="Importe a devolver">
            <input type="number" className={inputCls} placeholder="0.00" value={form.amount ?? ''} onChange={(e) => setF('amount', e.target.value)} />
          </Field>
          <Field label="Motivo">
            <input className={inputCls} value={form.reason ?? ''} onChange={(e) => setF('reason', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitDevolucion}>{saving ? 'Guardando...' : 'Crear Devolución'}</button>
          </div>
        </Modal>
      )}

      {/* Resolver Devolución */}
      {modal?.kind === 'resolve_dev' && (
        <Modal title={`Resolver devolución — ${modal.devolucion.folio}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">{modal.devolucion.customer_name} · {fmt(modal.devolucion.amount)}</p>
          <Field label="Tipo de resolución">
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="resolution" value="anticipo" checked={form.resolution === 'anticipo'} onChange={(e) => setF('resolution', e.target.value)} />
                <span className="text-sm">Convertir en anticipo disponible (ANT-xxxxx)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="resolution" value="abono_remision" checked={form.resolution === 'abono_remision'} onChange={(e) => setF('resolution', e.target.value)} />
                <span className="text-sm">Abonar directo a una remisión</span>
              </label>
            </div>
          </Field>
          {form.resolution === 'abono_remision' && (
            <Field label="Remisión a abonar">
              <RemisionSelect value={form.sales_document_id ?? ''} onChange={(v) => setF('sales_document_id', v)} />
            </Field>
          )}
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={btnPrimary} disabled={saving} onClick={submitResolveDevolucion}>{saving ? 'Resolviendo...' : 'Resolver'}</button>
          </div>
        </Modal>
      )}

      {/* Cruce manual conciliación */}
      {matchModal && (
        <Modal title={`Cruzar movimiento — ${matchModal.folio}`} onClose={() => setMatchModal(null)}>
          <p className="text-sm text-gray-600 mb-4">
            Movimiento banco: <strong>{fmt(matchModal.amount)}</strong> · {fmtDate(matchModal.movement_date)}
            {matchModal.clave_rastreo && <span className="text-xs text-gray-400 ml-2">({matchModal.clave_rastreo})</span>}
          </p>
          <Field label="Pago de cobranza a cruzar">
            <select className={inputCls} value={matchPayId} onChange={(e) => setMatchPayId(e.target.value)}>
              <option value="">Seleccionar pago...</option>
              {(concData?.solo_billing ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.folio} — {p.customer_name} — {fmt(p.amount)} — {fmtDate(p.payment_date)}
                </option>
              ))}
            </select>
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setMatchModal(null)}>Cancelar</button>
            <button
              className={btnPrimary}
              disabled={matchSaving || !matchPayId}
              onClick={async () => {
                if (!matchPayId) return;
                setMatchSaving(true);
                try {
                  await api.createConciliacionMatch({ movement_id: matchModal.id, movement_folio: matchModal.folio, payment_id: matchPayId });
                  setMatchModal(null);
                  const d = await api.getConciliacionData({ date_from: concFilter.date_from || undefined, date_to: concFilter.date_to || undefined, account_id: concFilter.account_id || undefined });
                  setConcData(d);
                } catch (e: any) {
                  setFormErr(e.message);
                } finally {
                  setMatchSaving(false);
                }
              }}
            >
              {matchSaving ? 'Cruzando...' : 'Confirmar cruce'}
            </button>
          </div>
        </Modal>
      )}

      {/* Cerrar Corte */}
      {modal?.kind === 'close_corte' && (
        <Modal title={`Cerrar corte — ${modal.cut.folio ?? modal.cut.id.slice(0, 8)}`} onClose={() => setModal(null)}>
          <p className="text-sm text-gray-600 mb-4">¿A qué cuenta se entrega el efectivo del corte?</p>
          <Field label="Cuenta destino">
            <select className={inputCls} value={form.account_id ?? ''} onChange={(e) => setF('account_id', e.target.value)}>
              <option value="">Seleccionar cuenta...</option>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
            </select>
          </Field>
          <Field label="Efectivo contado (opcional)">
            <input type="number" className={inputCls} placeholder="0.00" value={form.counted ?? ''} onChange={(e) => setF('counted', e.target.value)} />
          </Field>
          {formErr && <p className="text-red-600 text-sm mb-3">{formErr}</p>}
          <div className="flex gap-2 justify-end">
            <button className={btnSecondary} onClick={() => setModal(null)}>Cancelar</button>
            <button className={`${btnPrimary} bg-gray-800 hover:bg-black`} disabled={saving} onClick={submitCloseCut}>{saving ? 'Cerrando...' : 'Cerrar Corte'}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── Small sub-components ─────────────────────────────────────────────────────

function Section({ title, children, highlight }: { title: string; children: React.ReactNode; highlight?: boolean }) {
  const [open, setOpen] = useState(true);
  return (
    <div className={`rounded-xl border overflow-hidden ${highlight ? 'border-yellow-300' : 'border-gray-200'}`}>
      <button
        onClick={() => setOpen((p) => !p)}
        className={`w-full flex justify-between items-center px-5 py-3 text-sm font-semibold ${highlight ? 'bg-yellow-50 text-yellow-800' : 'bg-gray-50 text-gray-700'}`}
      >
        {title}
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && <div className="bg-white">{children}</div>}
    </div>
  );
}

function SortTh({
  col, sort, onSort, align = 'left', className = '', children,
}: {
  col: string;
  sort: { col: string; dir: 'asc' | 'desc' };
  onSort: (s: { col: string; dir: 'asc' | 'desc' }) => void;
  align?: 'left' | 'right' | 'center';
  className?: string;
  children: React.ReactNode;
}) {
  const active = sort.col === col;
  return (
    <th
      className={`px-3 py-3 cursor-pointer select-none whitespace-nowrap text-${align} ${className} hover:text-gray-800 ${active ? 'text-blue-600' : ''}`}
      onClick={() => onSort({ col, dir: active && sort.dir === 'desc' ? 'asc' : 'desc' })}
    >
      {children}
      <span className="ml-0.5 opacity-60">{active ? (sort.dir === 'desc' ? ' ↓' : ' ↑') : ' ↕'}</span>
    </th>
  );
}

function SimpleTable({ cols, rows }: { cols: string[]; rows: React.ReactNode[][] }) {
  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 text-gray-500 text-xs">
        <tr>{cols.map((c) => <th key={c} className="text-left px-4 py-2">{c}</th>)}</tr>
      </thead>
      <tbody>
        {rows.length === 0 && <tr><td colSpan={cols.length} className="text-center py-6 text-gray-400">Sin registros</td></tr>}
        {rows.map((row, i) => (
          <tr key={i} className="border-t border-gray-100">
            {row.map((cell, j) => <td key={j} className="px-4 py-2.5">{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
