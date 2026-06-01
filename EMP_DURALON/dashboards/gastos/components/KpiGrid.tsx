'use client';

import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

type Props = {
  total:        number;
  count:        number;
  avg:          number;
  totalMes:     number;
  totalMesAnt:  number;
  variacion:    number;
  topCategoria: string;
};

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style:                 'currency',
    currency:              'MXN',
    maximumFractionDigits: 0,
  }).format(n);
}

function VariIcon({ v }: { v: number }) {
  if (v > 1)  return <TrendingUp  size={16} className="text-red-500" />;
  if (v < -1) return <TrendingDown size={16} className="text-emerald-500" />;
  return <Minus size={16} className="text-slate-400" />;
}

export default function KpiGrid({
  total, count, avg, totalMes, totalMesAnt, variacion, topCategoria,
}: Props) {
  const mesNombre = new Date().toLocaleString('es-MX', { month: 'long', year: 'numeric' });
  const varSign   = variacion >= 0 ? '+' : '';
  const varColor  = variacion > 5 ? 'text-red-500' : variacion < -5 ? 'text-emerald-600' : 'text-slate-500';

  const cards = [
    {
      label: 'Gasto acumulado',
      value: mxn(total),
      sub:   `${count} movimientos en total`,
    },
    {
      label: `Mes en curso`,
      value: mxn(totalMes),
      sub:   totalMesAnt > 0
        ? <span className="flex items-center gap-1">{varSign}{variacion.toFixed(1)}% vs mes anterior <VariIcon v={variacion} /></span>
        : <span className={varColor}>Sin mes anterior</span>,
    },
    {
      label: 'Promedio por gasto',
      value: mxn(avg),
      sub:   'promedio acumulado',
    },
    {
      label: 'Categoría principal',
      value: topCategoria || '—',
      sub:   'mayor gasto total',
      mono:  true,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{c.label}</p>
          <p className={`mt-2 text-2xl font-semibold text-slate-900 ${c.mono ? 'text-base' : ''}`}>{c.value}</p>
          <p className={`mt-1 text-xs ${varColor}`}>{c.sub}</p>
        </div>
      ))}
    </div>
  );
}
