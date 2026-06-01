'use client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

type Categoria = { categoria: string; total: number; count: number };
type Props     = { data: Categoria[] };

const COLORS = ['#0f172a', '#1e3a5f', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'];

function mxn(n: number) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN', maximumFractionDigits: 0,
  }).format(n);
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as Categoria;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-lg text-xs">
      <p className="font-semibold text-slate-800">{label}</p>
      <p className="mt-1 text-slate-600">Total: <span className="font-medium text-slate-900">{mxn(d.total)}</span></p>
      <p className="text-slate-600">Movs: <span className="font-medium text-slate-900">{d.count}</span></p>
      <p className="text-slate-600">Promedio: <span className="font-medium text-slate-900">{mxn(d.total / d.count)}</span></p>
    </div>
  );
}

export default function ExpenseChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        Sin datos por categoría
      </div>
    );
  }

  // Show top 8 categories
  const top = [...data].sort((a, b) => b.total - a.total).slice(0, 8);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={top} margin={{ top: 4, right: 8, left: 8, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="categoria"
          tick={{ fontSize: 11, fill: '#64748b' }}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          tick={{ fontSize: 11, fill: '#64748b' }}
          width={48}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="total" radius={[4, 4, 0, 0]}>
          {top.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
