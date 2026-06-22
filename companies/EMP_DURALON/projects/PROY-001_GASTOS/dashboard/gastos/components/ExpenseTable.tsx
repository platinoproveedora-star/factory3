'use client';

import { useState, useMemo } from 'react';
import { Search, Download, ChevronLeft, ChevronRight, Plus, Trash2, Pencil, Check, X, ChevronUp, ChevronDown } from 'lucide-react';
import type { BankAccount, Gasto } from '../lib/db';
import { gastosToCSV, downloadCSV } from '../lib/export';
import projectContext from '../project-context.json';

type Props = { gastos: Gasto[]; bankAccounts: BankAccount[] };

const PAGE_SIZE = 50;
const FACTORY_URL = process.env.NEXT_PUBLIC_FACTORY_API_URL ?? '';
const WRITE_KEY   = process.env.NEXT_PUBLIC_WRITE_KEY ?? '';
const SKILL = 'vertical_client_expenses/client_expenses_run';
const BANKS_RECONCILE_SKILL = 'vertical_erp_banks/erp_banks_expense_reconcile';
const BASE_CTX = {
  schema: projectContext.schema,
  empresa_id: projectContext.company_id,
  project_code: projectContext.project_code,
  module_code: projectContext.module_code,
  dry_run: false,
};
const BANKS_RECONCILE_CTX = {
  banks_schema: (projectContext as any).banks_schema,
  expenses_schema: projectContext.schema,
  company_id: projectContext.company_id,
  banks_project_code: (projectContext as any).banks_project_code,
  banks_module_code: (projectContext as any).banks_module_code ?? 'banks',
  expenses_project_code: projectContext.project_code,
  expense_module_code: projectContext.module_code,
  dry_run: false,
};

// Fallback — se sobreescribe con categorías reales de los datos
const CATEGORIES_DEFAULT = [
  'combustible','gastos varios','taller mecanico','papeleria',
  'telmex','gas','internet','recargas celulares','nomina','gps','imss','sat',
];

const METHOD_LABEL: Record<string, string> = {
  foto: '📷', manual: '⌨️', api: '🔌', ai_ocr: '🤖', import_excel: '📊',
};

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 2 }).format(n);
}

function fmtDate(s: string) {
  if (!s) return '—';
  const [y, m, d] = s.split('-');
  const months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return `${d} ${months[Number(m) - 1]} ${y}`;
}

async function skillPost(action: string, extra: object, skill = SKILL, baseCtx: Record<string, unknown> = BASE_CTX) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (WRITE_KEY) headers['x-write-key'] = WRITE_KEY;
  const res = await fetch(`${FACTORY_URL}/data/${skill}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...baseCtx, action, ...extra }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Error');
  if (json?.ok === false) throw new Error(json.error ?? 'Error en skill');
  return json;
}

function skillData(result: any) {
  return result?.data ?? result ?? {};
}

async function assignExpenseWithdrawal(expense: { id?: string; folio?: string }, accountId: string, notes?: string) {
  if (!accountId || (!expense.id && !expense.folio)) return;
  await skillPost('assign', {
    expense_id: expense.id,
    expense_folio: expense.folio,
    source_account_id: accountId,
    performed_by: 'dashboard_gastos',
    notes,
  }, BANKS_RECONCILE_SKILL, BANKS_RECONCILE_CTX);
}

async function cancelExpenseWithdrawal(expense: { id?: string; folio?: string }, reason: string) {
  if (!expense.id && !expense.folio) return;
  try {
    await skillPost('cancel', {
      expense_id: expense.id,
      expense_folio: expense.folio,
      performed_by: 'dashboard_gastos',
      reason,
    }, BANKS_RECONCILE_SKILL, BANKS_RECONCILE_CTX);
  } catch (error: any) {
    const message = String(error?.message || '').toLowerCase();
    if (!message.includes('asignacion no encontrada')) throw error;
  }
}

type EditDraft = { monto: string; fecha: string; descripcion: string; categoria: string; vehiculo: string; cta_retiro_id: string };

export default function ExpenseTable({ gastos: initialGastos, bankAccounts }: Props) {
  const [gastos, setGastos]     = useState<Gasto[]>(initialGastos);
  const [q, setQ]               = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [page, setPage]         = useState(0);
  const [sortCol, setSortCol]   = useState<keyof Gasto>('fecha');
  const [sortDir, setSortDir]   = useState<'asc'|'desc'>('desc');
  const [editingFolio, setEdit] = useState<string | null>(null);
  const [draft, setDraft]       = useState<EditDraft>({ monto: '', fecha: '', descripcion: '', categoria: '', vehiculo: '', cta_retiro_id: '' });
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState('');
  const [adding, setAdding]     = useState(false);

  // Categorías dinámicas desde los datos existentes
  const CATEGORIES = useMemo(() => {
    const fromData = Array.from(new Set(gastos.map(g => g.categoria).filter(Boolean))).sort();
    return fromData.length > 0 ? fromData : CATEGORIES_DEFAULT;
  }, [gastos]);

  const [newRow, setNewRow] = useState<EditDraft>({
    monto: '', fecha: new Date().toISOString().slice(0,10),
    descripcion: '', categoria: CATEGORIES_DEFAULT[0], vehiculo: '', cta_retiro_id: '',
  });

  const accountById = useMemo(() => new Map(bankAccounts.map(account => [account.id, account])), [bankAccounts]);

  const filtered = useMemo(() => {
    const lq = q.toLowerCase().trim();
    const base = gastos.filter(g => {
      if (lq && !(
        g.descripcion.toLowerCase().includes(lq) ||
        g.categoria.toLowerCase().includes(lq) ||
        g.nombre_usuario.toLowerCase().includes(lq) ||
        g.folio.toLowerCase().includes(lq)
      )) return false;
      if (fechaDesde && g.fecha < fechaDesde) return false;
      if (fechaHasta && g.fecha > fechaHasta) return false;
      return true;
    });

    base.sort((a, b) => {
      const av = a[sortCol] ?? '';
      const bv = b[sortCol] ?? '';
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return base;
  }, [gastos, q, sortCol, sortDir]);

  function toggleSort(col: keyof Gasto) {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('desc'); }
    setPage(0);
  }

  function SortIcon({ col }: { col: keyof Gasto }) {
    if (sortCol !== col) return <ChevronUp size={11} className="opacity-20" />;
    return sortDir === 'asc' ? <ChevronUp size={11} /> : <ChevronDown size={11} />;
  }

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const slice      = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function startEdit(g: Gasto) {
    setEdit(g.folio);
    setDraft({ monto: String(g.monto), fecha: g.fecha, descripcion: g.descripcion, categoria: g.categoria, vehiculo: g.vehiculo ?? '', cta_retiro_id: g.cta_retiro_id ?? '' });
    setError('');
  }

  function cancelEdit() { setEdit(null); setError(''); }

  async function saveEdit(folio: string) {
    setSaving(true); setError('');
    try {
      const previous = gastos.find(g => g.folio === folio);
      const previousAccountId = previous?.cta_retiro_id || '';
      const nextAccountId = draft.cta_retiro_id || '';
      const accountChanged = previousAccountId !== nextAccountId;

      const updateResult = await skillPost('update_expense', {
        folio,
        monto:       parseFloat(draft.monto),
        fecha:       draft.fecha,
        descripcion: draft.descripcion,
        categoria:   draft.categoria,
        vehiculo:    draft.vehiculo || null,
        cta_retiro_id: draft.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(draft.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(draft.cta_retiro_id)?.account_name || null,
      });
      const updated = skillData(updateResult).gasto ?? {};
      const expenseRef = { id: updated.id, folio: updated.folio ?? folio };
      if (accountChanged && previousAccountId) {
        await cancelExpenseWithdrawal(expenseRef, 'cambio_cta_retiro_desde_gastos');
      }
      if (nextAccountId) {
        await assignExpenseWithdrawal(expenseRef, nextAccountId, draft.descripcion);
      }
      setGastos(prev => prev.map(g =>
        g.folio === folio
          ? {
              ...g,
              monto: parseFloat(draft.monto),
              fecha: draft.fecha,
              descripcion: draft.descripcion,
              categoria: draft.categoria,
              vehiculo: draft.vehiculo || null,
              cta_retiro_id: draft.cta_retiro_id || null,
              cta_retiro_folio: accountById.get(draft.cta_retiro_id)?.folio || null,
              cta_retiro_nombre: accountById.get(draft.cta_retiro_id)?.account_name || null,
            }
          : g
      ));
      setEdit(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteRow(folio: string) {
    if (!confirm(`¿Eliminar ${folio}? Esta acción no se puede deshacer.`)) return;
    setSaving(true); setError('');
    try {
      await skillPost('delete_expense', { folio });
      setGastos(prev => prev.filter(g => g.folio !== folio));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function addExpense() {
    if (!newRow.monto || !newRow.fecha || !newRow.categoria) {
      setError('Monto, fecha y categoría son requeridos'); return;
    }
    setSaving(true); setError('');
    try {
      // Resolver usuario "dashboard" — el skill lo crea si no existe
      const userResult = await skillPost('register_user', {
        nombre: 'dashboard',
        telegram_chat_id: 'dashboard',
      });
      const usuario_id = userResult?.user?.id ?? userResult?.data?.user?.id ?? '';

      const result = await skillPost('save_expense', {
        usuario_id,
        monto:          parseFloat(newRow.monto),
        fecha:          newRow.fecha,
        descripcion:    newRow.descripcion,
        categoria:      newRow.categoria,
        vehiculo:       newRow.vehiculo || null,
        cta_retiro_id:  newRow.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(newRow.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(newRow.cta_retiro_id)?.account_name || null,
        metodo_captura: 'dashboard',
      });
      const saved = skillData(result).gasto ?? {};
      if (newRow.cta_retiro_id) {
        await assignExpenseWithdrawal({ id: saved.id, folio: saved.folio }, newRow.cta_retiro_id, newRow.descripcion);
      }
      setGastos(prev => [{
        folio:          saved.folio ?? '—',
        fecha:          newRow.fecha,
        monto:          parseFloat(newRow.monto),
        descripcion:    newRow.descripcion,
        metodo_captura: 'dashboard',
        categoria:      newRow.categoria,
        vehiculo:       newRow.vehiculo || null,
        cta_retiro_id:  newRow.cta_retiro_id || null,
        cta_retiro_folio: accountById.get(newRow.cta_retiro_id)?.folio || null,
        cta_retiro_nombre: accountById.get(newRow.cta_retiro_id)?.account_name || null,
        nombre_usuario: 'dashboard',
      }, ...prev]);
      setNewRow({ monto: '', fecha: new Date().toISOString().slice(0,10), descripcion: '', categoria: 'combustible', vehiculo: '', cta_retiro_id: '' });
      setAdding(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  function handleExport() {
    const csv   = gastosToCSV(filtered);
    const today = new Date().toISOString().slice(0, 10);
    downloadCSV(`gastos-duralon-${today}.csv`, csv);
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar descripción, categoría, folio…"
            value={q}
            onChange={e => { setQ(e.target.value); setPage(0); }}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-slate-400"
          />
        </div>
        <input type="date" value={fechaDesde}
          onChange={e => { setFechaDesde(e.target.value); setPage(0); }}
          title="Desde"
          className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm outline-none focus:border-slate-400 text-slate-600" />
        <input type="date" value={fechaHasta}
          onChange={e => { setFechaHasta(e.target.value); setPage(0); }}
          title="Hasta"
          className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm outline-none focus:border-slate-400 text-slate-600" />
        {(fechaDesde || fechaHasta) && (
          <button onClick={() => { setFechaDesde(''); setFechaHasta(''); setPage(0); }}
            className="text-xs text-slate-400 hover:text-slate-700">✕</button>
        )}
        <span className="text-xs text-slate-500 whitespace-nowrap">{filtered.length} resultados</span>
        <button
          onClick={() => { setAdding(true); setError(''); }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700"
        >
          <Plus size={14} /> Nuevo gasto
        </button>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50"
        >
          <Download size={14} /> CSV
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{error}</div>
      )}

      {/* Nuevo gasto form */}
      {adding && (
        <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="text-xs font-semibold text-blue-700 mb-3">Nuevo gasto</p>
          <div className="flex flex-wrap gap-2 items-end">
            <div>
              <label className="text-xs text-slate-500">Monto</label>
              <input type="number" placeholder="0.00" min="0" value={newRow.monto}
                onChange={e => setNewRow(p => ({...p, monto: e.target.value}))}
                className="block w-28 rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5" />
            </div>
            <div>
              <label className="text-xs text-slate-500">Fecha</label>
              <input type="date" value={newRow.fecha}
                onChange={e => setNewRow(p => ({...p, fecha: e.target.value}))}
                className="block rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5" />
            </div>
            <div>
              <label className="text-xs text-slate-500">Categoría</label>
              <select value={newRow.categoria}
                onChange={e => setNewRow(p => ({...p, categoria: e.target.value}))}
                className="block rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5">
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Vehículo</label>
              <input type="text" placeholder="ej: Torton 01" value={newRow.vehiculo}
                onChange={e => setNewRow(p => ({...p, vehiculo: e.target.value}))}
                className="block rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5 w-32" />
            </div>
            <div>
              <label className="text-xs text-slate-500">Cta retiro</label>
              <select value={newRow.cta_retiro_id}
                onChange={e => setNewRow(p => ({...p, cta_retiro_id: e.target.value}))}
                className="block rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5 min-w-[180px]">
                <option value="">Sin asignar</option>
                {bankAccounts.map(account => <option key={account.id} value={account.id}>{account.account_name}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[160px]">
              <label className="text-xs text-slate-500">Descripción</label>
              <input type="text" placeholder="opcional" value={newRow.descripcion}
                onChange={e => setNewRow(p => ({...p, descripcion: e.target.value}))}
                className="block w-full rounded border border-slate-200 px-2 py-1.5 text-sm mt-0.5" />
            </div>
            <button onClick={addExpense} disabled={saving}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
              <Check size={14} /> Guardar
            </button>
            <button onClick={() => { setAdding(false); setError(''); }}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">
              <X size={14} /> Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-100 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {([
                ['Folio','folio'],['Fecha','fecha'],['Categoría','categoria'],
                ['Vehículo','vehiculo'],['Cta retiro','cta_retiro_nombre'],['Descripción','descripcion'],
                ['Usuario','nombre_usuario'],['Método','metodo_captura'],['Monto','monto'],['','']
              ] as [string, string][]).map(([label, col]) => (
                <th key={label}
                  onClick={() => col && toggleSort(col as keyof Gasto)}
                  className={`px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 ${col ? 'cursor-pointer hover:text-slate-800 select-none' : ''}`}>
                  <span className="inline-flex items-center gap-1">
                    {label}{col && <SortIcon col={col as keyof Gasto} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {slice.length === 0 ? (
              <tr><td colSpan={10} className="py-10 text-center text-sm text-slate-400">Sin resultados</td></tr>
            ) : slice.map(g => {
              const isEditing = editingFolio === g.folio;
              return (
                <tr key={g.folio} className={isEditing ? 'bg-yellow-50' : 'group hover:bg-slate-50'}>
                  <td className="px-3 py-2 font-mono text-xs text-slate-600">{g.folio}</td>

                  {/* Fecha */}
                  <td className="px-3 py-2 whitespace-nowrap">
                    {isEditing
                      ? <input type="date" value={draft.fecha}
                          onChange={e => setDraft(p => ({...p, fecha: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs w-32" />
                      : fmtDate(g.fecha)}
                  </td>

                  {/* Categoría */}
                  <td className="px-3 py-2">
                    {isEditing
                      ? <select value={draft.categoria}
                          onChange={e => setDraft(p => ({...p, categoria: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs">
                          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                        </select>
                      : <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">{g.categoria || '—'}</span>}
                  </td>

                  {/* Vehículo */}
                  <td className="px-3 py-2">
                    {isEditing
                      ? <input type="text" value={draft.vehiculo} placeholder="unidad"
                          onChange={e => setDraft(p => ({...p, vehiculo: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs w-24" />
                      : <span className="text-xs text-slate-600">{g.vehiculo || '—'}</span>}
                  </td>

                  {/* Cuenta retiro */}
                  <td className="px-3 py-2">
                    {isEditing
                      ? <select value={draft.cta_retiro_id}
                          onChange={e => setDraft(p => ({...p, cta_retiro_id: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs min-w-[150px]">
                          <option value="">Sin asignar</option>
                          {bankAccounts.map(account => <option key={account.id} value={account.id}>{account.account_name}</option>)}
                        </select>
                      : <span className="text-xs text-slate-600">{g.cta_retiro_nombre || 'Sin asignar'}</span>}
                  </td>

                  {/* Descripción */}
                  <td className="px-3 py-2 max-w-[200px]">
                    {isEditing
                      ? <input type="text" value={draft.descripcion}
                          onChange={e => setDraft(p => ({...p, descripcion: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs w-full" />
                      : <span className="truncate block" title={g.descripcion}>{g.descripcion || '—'}</span>}
                  </td>

                  <td className="px-3 py-2 text-slate-600">{g.nombre_usuario || '—'}</td>
                  <td className="px-3 py-2 text-slate-400 text-xs">{METHOD_LABEL[g.metodo_captura] ?? g.metodo_captura}</td>

                  {/* Monto */}
                  <td className="px-3 py-2 text-right font-semibold text-slate-900">
                    {isEditing
                      ? <input type="number" min="0" value={draft.monto}
                          onChange={e => setDraft(p => ({...p, monto: e.target.value}))}
                          className="rounded border border-slate-300 px-1 py-0.5 text-xs w-24 text-right" />
                      : mxn(g.monto)}
                  </td>

                  {/* Acciones */}
                  <td className="px-3 py-2 whitespace-nowrap">
                    {isEditing ? (
                      <div className="flex gap-1">
                        <button onClick={() => saveEdit(g.folio)} disabled={saving}
                          className="rounded bg-emerald-100 p-1 text-emerald-700 hover:bg-emerald-200 disabled:opacity-40">
                          <Check size={13} />
                        </button>
                        <button onClick={cancelEdit}
                          className="rounded bg-slate-100 p-1 text-slate-600 hover:bg-slate-200">
                          <X size={13} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => startEdit(g)}
                          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                          <Pencil size={13} />
                        </button>
                        <button onClick={() => deleteRow(g.folio)} disabled={saving}
                          className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
          <span>Pág {safePage + 1} de {totalPages}</span>
          <div className="flex gap-2">
            <button disabled={safePage === 0} onClick={() => setPage(p => Math.max(0, p - 1))}
              className="rounded border border-slate-200 p-1 disabled:opacity-40 hover:bg-slate-50">
              <ChevronLeft size={16} />
            </button>
            <button disabled={safePage >= totalPages - 1} onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              className="rounded border border-slate-200 p-1 disabled:opacity-40 hover:bg-slate-50">
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
