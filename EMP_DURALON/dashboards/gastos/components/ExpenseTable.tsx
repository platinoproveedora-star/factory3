'use client';

import { useState, useMemo } from 'react';
import { Search, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Gasto } from '../lib/db';
import { gastosToCSV, downloadCSV } from '../lib/export';

type Props = { gastos: Gasto[] };

const PAGE_SIZE = 50;

const METHOD_LABEL: Record<string, string> = {
  foto:    '📷 foto',
  manual:  '⌨️ manual',
  api:     '🔌 api',
};

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN', maximumFractionDigits: 2,
  }).format(n);
}

function fmtDate(s: string) {
  if (!s) return '—';
  const [y, m, d] = s.split('-');
  const months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return `${d} ${months[Number(m) - 1]} ${y}`;
}

export default function ExpenseTable({ gastos }: Props) {
  const [q, setQ]       = useState('');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const lq = q.toLowerCase().trim();
    if (!lq) return gastos;
    return gastos.filter((g) =>
      g.descripcion.toLowerCase().includes(lq) ||
      g.categoria.toLowerCase().includes(lq) ||
      g.nombre_usuario.toLowerCase().includes(lq) ||
      g.folio.toLowerCase().includes(lq)
    );
  }, [gastos, q]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const slice      = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function handleSearch(v: string) {
    setQ(v);
    setPage(0);
  }

  function handleExport() {
    const csv      = gastosToCSV(filtered);
    const today    = new Date().toISOString().slice(0, 10);
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
            placeholder="Buscar por descripción, categoría, usuario…"
            value={q}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-slate-400 focus:ring-1 focus:ring-slate-200"
          />
        </div>
        <span className="text-xs text-slate-500 whitespace-nowrap">
          {filtered.length} resultado{filtered.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50"
        >
          <Download size={14} /> Exportar CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-100 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {['Folio','Fecha','Categoría','Descripción','Usuario','Método','Monto'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {slice.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-10 text-center text-sm text-slate-400">
                  Sin resultados
                </td>
              </tr>
            ) : (
              slice.map((g) => (
                <tr key={g.folio} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{g.folio}</td>
                  <td className="px-4 py-2.5 whitespace-nowrap text-slate-700">{fmtDate(g.fecha)}</td>
                  <td className="px-4 py-2.5">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {g.categoria || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 max-w-[220px] truncate text-slate-800" title={g.descripcion}>
                    {g.descripcion || '—'}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{g.nombre_usuario || '—'}</td>
                  <td className="px-4 py-2.5 text-slate-500 text-xs">
                    {METHOD_LABEL[g.metodo_captura] ?? g.metodo_captura}
                  </td>
                  <td className="px-4 py-2.5 text-right font-semibold text-slate-900">
                    {mxn(g.monto)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
          <span>
            Pág {safePage + 1} de {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={safePage === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="rounded border border-slate-200 p-1 disabled:opacity-40 hover:bg-slate-50"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              disabled={safePage >= totalPages - 1}
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              className="rounded border border-slate-200 p-1 disabled:opacity-40 hover:bg-slate-50"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
