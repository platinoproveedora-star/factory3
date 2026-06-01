'use client';

import { useState, useMemo } from 'react';
import { Search, Download, ChevronLeft, ChevronRight, Plus, Trash2, Pencil, Check, X } from 'lucide-react';
import type { Gasto } from '../lib/db';
import { gastosToCSV, downloadCSV } from '../lib/export';

type Props = { gastos: Gasto[] };

const PAGE_SIZE = 50;
const FACTORY_URL = process.env.NEXT_PUBLIC_FACTORY_API_URL ?? '';
const SKILL = 'vertical_client_expenses/client_expenses_run';
const BASE_CTX = { schema: 'uc101_proy001', empresa_id: 'EMP_DURALON', project_code: 'PROY-001', module_code: 'gastos', dry_run: false };

const CATEGORIES = [
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

async function skillPost(action: string, extra: object) {
  const res = await fetch(`${FACTORY_URL}/data/${SKILL}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...BASE_CTX, action, ...extra }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? 'Error');
  return json;
}

type EditDraft = { monto: string; fecha: string; descripcion: string; categoria: string; vehiculo: string };

export default function ExpenseTable({ gastos: initialGastos }: Props) {
  const [gastos, setGastos]     = useState<Gasto[]>(initialGastos);
  const [q, setQ]               = useState('');
  const [page, setPage]         = useState(0);
  const [editingFolio, setEdit] = useState<string | null>(null);
  const [draft, setDraft]       = useState<EditDraft>({ monto: '', fecha: '', descripcion: '', categoria: '', vehiculo: '' });
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState('');
  const [adding, setAdding]     = useState(false);
  const [newRow, setNewRow]     = useState<EditDraft>({ monto: '', fecha: new Date().toISOString().slice(0,10), descripcion: '', categoria: 'combustible', vehiculo: '' });

  const filtered = useMemo(() => {
    const lq = q.toLowerCase().trim();
    if (!lq) return gastos;
    return gastos.filter(g =>
      g.descripcion.toLowerCase().includes(lq) ||
      g.categoria.toLowerCase().includes(lq) ||
      g.nombre_usuario.toLowerCase().includes(lq) ||
      g.folio.toLowerCase().includes(lq)
    );
  }, [gastos, q]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const slice      = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function startEdit(g: Gasto) {
    setEdit(g.folio);
    setDraft({ monto: String(g.monto), fecha: g.fecha, descripcion: g.descripcion, categoria: g.categoria, vehiculo: g.vehiculo ?? '' });
    setError('');
  }

  function cancelEdit() { setEdit(null); setError(''); }

  async function saveEdit(folio: string) {
    setSaving(true); setError('');
    try {
      await skillPost('update_expense', {
        folio,
        monto:       parseFloat(draft.monto),
        fecha:       draft.fecha,
        descripcion: draft.descripcion,
        categoria:   draft.categoria,
        vehiculo:    draft.vehiculo || null,
      });
      setGastos(prev => prev.map(g =>
        g.folio === folio
          ? { ...g, monto: parseFloat(draft.monto), fecha: draft.fecha, descripcion: draft.descripcion, categoria: draft.categoria, vehiculo: draft.vehiculo || null }
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
        metodo_captura: 'dashboard',
      });
      const saved = result.gasto ?? {};
      setGastos(prev => [{
        folio:          saved.folio ?? '—',
        fecha:          newRow.fecha,
        monto:          parseFloat(newRow.monto),
        descripcion:    newRow.descripcion,
        metodo_captura: 'dashboard',
        categoria:      newRow.categoria,
        vehiculo:       newRow.vehiculo || null,
        nombre_usuario: 'dashboard',
      }, ...prev]);
      setNewRow({ monto: '', fecha: new Date().toISOString().slice(0,10), descripcion: '', categoria: 'combustible', vehiculo: '' });
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
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar descripción, categoría, usuario…"
            value={q}
            onChange={e => { setQ(e.target.value); setPage(0); }}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-slate-400"
          />
        </div>
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
              <input type="number" placeholder="0.00" value={newRow.monto}
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
              {['Folio','Fecha','Categoría','Vehículo','Descripción','Usuario','Método','Monto',''].map(h => (
                <th key={h} className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {slice.length === 0 ? (
              <tr><td colSpan={9} className="py-10 text-center text-sm text-slate-400">Sin resultados</td></tr>
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
                      ? <input type="number" value={draft.monto}
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
