'use client';

import type { Gasto } from '../lib/db';

type Props = { gastos: Gasto[] };

const MONTH_NAMES: Record<string, string> = {
  '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
  '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
  '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic',
};

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
  }).format(n);
}

export default function CategoryMonthlyTable({ gastos }: Props) {
  // Obtener meses únicos ordenados desc (más reciente primero)
  const monthSet = new Set(gastos.map(g => g.fecha.slice(0, 7)));
  const allMonths = Array.from(monthSet).sort((a, b) => b.localeCompare(a));
  const months = allMonths.slice(0, 6);
  const hasMore = allMonths.length > 6;

  // Obtener categorías únicas
  const catSet = new Set(gastos.map(g => g.categoria).filter(Boolean));
  const categories = Array.from(catSet);

  // Matriz: categoria → mes → total
  const matrix: Record<string, Record<string, number>> = {};
  for (const g of gastos) {
    const month = g.fecha.slice(0, 7);
    const cat   = g.categoria || 'Sin categoría';
    if (!matrix[cat]) matrix[cat] = {};
    matrix[cat][month] = (matrix[cat][month] ?? 0) + g.monto;
  }

  // Ordenar categorías por total general desc
  const sortedCats = categories.sort((a, b) => {
    const totA = Object.values(matrix[a] ?? {}).reduce((s, v) => s + v, 0);
    const totB = Object.values(matrix[b] ?? {}).reduce((s, v) => s + v, 0);
    return totB - totA;
  });

  // Color por intensidad relativa por columna
  const colMax: Record<string, number> = {};
  for (const m of months) {
    colMax[m] = Math.max(...sortedCats.map(c => matrix[c]?.[m] ?? 0), 1);
  }

  if (!months.length || !sortedCats.length) {
    return <p className="py-8 text-center text-sm text-slate-400">Sin datos</p>;
  }

  const currentMonth = new Date().toISOString().slice(0, 7);

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 whitespace-nowrap">
              Categoría
            </th>
            {months.map(m => {
              const [y, mo] = m.split('-');
              return (
                <th key={m} className={`px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide whitespace-nowrap ${m === currentMonth ? 'text-blue-600' : 'text-slate-500'}`}>
                  {MONTH_NAMES[mo]} {y.slice(2)}
                  {m === currentMonth && <span className="ml-1 text-[9px] text-blue-400">●</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {sortedCats.map(cat => (
            <tr key={cat} className="hover:bg-slate-50">
              <td className="px-4 py-2.5 font-medium text-slate-800 whitespace-nowrap">{cat}</td>
              {months.map(m => {
                const val = matrix[cat]?.[m] ?? 0;
                const intensity = val > 0 ? Math.round((val / colMax[m]) * 80) + 10 : 0;
                return (
                  <td key={m} className="px-4 py-2.5 text-right">
                    {val > 0 ? (
                      <span
                        className="inline-block rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: `rgba(15, 23, 42, ${intensity / 100})`,
                          color: intensity > 50 ? '#fff' : '#1e293b',
                        }}
                      >
                        {mxn(val)}
                      </span>
                    ) : (
                      <span className="text-slate-200">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-50">
          <tr>
            <td className="px-4 py-2.5 text-xs font-semibold text-slate-500">Total mes</td>
            {months.map(m => {
              const total = sortedCats.reduce((s, c) => s + (matrix[c]?.[m] ?? 0), 0);
              return (
                <td key={m} className={`px-4 py-2.5 text-right text-xs font-bold ${m === currentMonth ? 'text-blue-700' : 'text-slate-700'}`}>
                  {mxn(total)}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
      {hasMore && (
        <p className="mt-2 text-[11px] text-slate-400 text-right">
          Mostrando los últimos 6 meses · {allMonths.length} meses en total
        </p>
      )}
    </div>
  );
}
