'use client';

import type { Gasto } from '../lib/db';

type Props = { gastos: Gasto[] };

const MONTH_NAMES: Record<string, string> = {
  '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
  '05': 'Mayo',  '06': 'Junio',   '07': 'Julio', '08': 'Agosto',
  '09': 'Sep',   '10': 'Octubre', '11': 'Nov',   '12': 'Dic',
};

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
  }).format(n);
}

export default function MonthlyTable({ gastos }: Props) {
  const currentMonth = new Date().toISOString().slice(0, 7);

  // Agrupar por mes
  const byMonth: Record<string, { total: number; count: number }> = {};
  for (const g of gastos) {
    const month = g.fecha.slice(0, 7);
    if (!byMonth[month]) byMonth[month] = { total: 0, count: 0 };
    byMonth[month].total += g.monto;
    byMonth[month].count += 1;
  }

  const months = Object.entries(byMonth)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([month, data]) => ({ month, ...data }));

  const currentTotal = byMonth[currentMonth]?.total ?? 0;

  if (!months.length) {
    return <p className="py-8 text-center text-sm text-slate-400">Sin datos mensuales</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {['Mes', 'Total', 'Movs', 'vs Mes Actual'].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {months.map(({ month, total, count }) => {
            const [year, m] = month.split('-');
            const label = `${MONTH_NAMES[m] ?? m} ${year}`;
            const isCurrent = month === currentMonth;

            let badge = <span className="text-slate-300">—</span>;
            if (!isCurrent && currentTotal > 0) {
              const diff = ((total - currentTotal) / currentTotal) * 100;
              if (diff > 5) {
                badge = (
                  <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">
                    ↑ {diff.toFixed(0)}% más alto
                  </span>
                );
              } else if (diff < -5) {
                badge = (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    ↓ {Math.abs(diff).toFixed(0)}% más bajo
                  </span>
                );
              } else {
                badge = <span className="text-xs text-slate-400">≈ similar</span>;
              }
            }

            return (
              <tr key={month} className={isCurrent ? 'bg-blue-50' : 'hover:bg-slate-50'}>
                <td className="px-4 py-2.5 font-medium text-slate-800">
                  {label}
                  {isCurrent && (
                    <span className="ml-2 rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-blue-600">
                      actual
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 font-semibold text-slate-900">{mxn(total)}</td>
                <td className="px-4 py-2.5 text-slate-500">{count}</td>
                <td className="px-4 py-2.5">{badge}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
