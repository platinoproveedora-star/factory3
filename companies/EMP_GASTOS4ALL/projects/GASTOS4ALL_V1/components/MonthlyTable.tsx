"use client";

import type { Gasto } from "@/lib/db";

const MONTH_NAMES: Record<string, string> = {
  "01": "Enero", "02": "Febrero", "03": "Marzo",  "04": "Abril",
  "05": "Mayo",  "06": "Junio",   "07": "Julio",  "08": "Agosto",
  "09": "Sep",   "10": "Octubre", "11": "Nov",    "12": "Dic",
};

function mxn(n: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
}

export default function MonthlyTable({ gastos }: { gastos: Gasto[] }) {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const byMonth: Record<string, { total: number; count: number }> = {};
  for (const g of gastos) {
    const m = g.fecha.slice(0, 7);
    if (!byMonth[m]) byMonth[m] = { total: 0, count: 0 };
    byMonth[m].total += g.monto;
    byMonth[m].count += 1;
  }
  const months = Object.entries(byMonth)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([month, data]) => ({ month, ...data }));
  const currentTotal = byMonth[currentMonth]?.total ?? 0;

  if (!months.length) return <p className="py-8 text-center text-sm text-muted">Sin datos mensuales</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="table-head">
          <tr>
            {["Mes", "Total", "Movs", "vs Mes Actual"].map((h) => (
              <th key={h} className="px-4 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50 bg-card">
          {months.map(({ month, total, count }) => {
            const [year, m] = month.split("-");
            const isCurrent = month === currentMonth;
            let badge = <span className="text-border">—</span>;
            if (!isCurrent && currentTotal > 0) {
              const diff = ((total - currentTotal) / currentTotal) * 100;
              if (diff > 5)
                badge = <span className="rounded-full bg-red-900/40 px-2 py-0.5 text-xs font-medium text-red-400">↑ {diff.toFixed(0)}% más alto</span>;
              else if (diff < -5)
                badge = <span className="rounded-full bg-emerald-900/40 px-2 py-0.5 text-xs font-medium text-emerald-400">↓ {Math.abs(diff).toFixed(0)}% más bajo</span>;
              else
                badge = <span className="text-xs text-muted">≈ similar</span>;
            }
            return (
              <tr key={month} className={isCurrent ? "bg-primary/10" : "hover:bg-slate-700/30"}>
                <td className="px-4 py-2.5 font-medium text-slate-200">
                  {MONTH_NAMES[m] ?? m} {year}
                  {isCurrent && <span className="ml-2 rounded-full bg-primary/20 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-primary">actual</span>}
                </td>
                <td className="px-4 py-2.5 font-semibold text-white">{mxn(total)}</td>
                <td className="px-4 py-2.5 text-muted">{count}</td>
                <td className="px-4 py-2.5">{badge}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
