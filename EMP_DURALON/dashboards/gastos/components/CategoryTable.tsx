'use client';

import type { StatCategoria } from '../lib/db';

type Props = { categorias: StatCategoria[]; total: number };

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
  }).format(n);
}

export default function CategoryTable({ categorias, total }: Props) {
  if (!categorias.length) {
    return <p className="py-8 text-center text-sm text-slate-400">Sin datos por categoría</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {['Categoría', 'Total', 'Movs', '% del total'].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {categorias.map((c, i) => {
            const pct = total > 0 ? Math.round((c.total / total) * 100) : 0;
            return (
              <tr key={c.categoria} className="hover:bg-slate-50">
                <td className="px-4 py-2.5 font-medium text-slate-800">
                  <span className="mr-2 text-slate-400 text-xs">#{i + 1}</span>
                  {c.categoria}
                </td>
                <td className="px-4 py-2.5 font-semibold text-slate-900">{mxn(c.total)}</td>
                <td className="px-4 py-2.5 text-slate-500">{c.count}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full bg-slate-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500">{pct}%</span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot className="bg-slate-50">
          <tr>
            <td className="px-4 py-2.5 text-xs font-semibold text-slate-500">Total</td>
            <td className="px-4 py-2.5 font-bold text-slate-900">{mxn(total)}</td>
            <td className="px-4 py-2.5 text-xs text-slate-500">
              {categorias.reduce((s, c) => s + c.count, 0)} movs
            </td>
            <td className="px-4 py-2.5 text-xs text-slate-500">100%</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
