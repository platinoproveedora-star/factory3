"use client";

import type { Gasto } from "@/lib/db";

const MONTH_NAMES: Record<string, string> = {
  "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
  "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
  "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic",
};

function mxn(n: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
}

export default function CategoryMonthlyTable({ gastos }: { gastos: Gasto[] }) {
  const monthSet  = new Set(gastos.map((g) => g.fecha.slice(0, 7)));
  const allMonths = Array.from(monthSet).sort((a, b) => b.localeCompare(a));
  const months    = allMonths.slice(0, 6);
  const hasMore   = allMonths.length > 6;
  const catSet    = new Set(gastos.map((g) => g.categoria).filter(Boolean));
  const matrix: Record<string, Record<string, number>> = {};
  for (const g of gastos) {
    const m = g.fecha.slice(0, 7);
    const c = g.categoria || "Sin categoría";
    if (!matrix[c]) matrix[c] = {};
    matrix[c][m] = (matrix[c][m] ?? 0) + g.monto;
  }
  const sortedCats = Array.from(catSet).sort((a, b) => {
    const ta = Object.values(matrix[a] ?? {}).reduce((s, v) => s + v, 0);
    const tb = Object.values(matrix[b] ?? {}).reduce((s, v) => s + v, 0);
    return tb - ta;
  });
  const colMax: Record<string, number> = {};
  for (const m of months) colMax[m] = Math.max(...sortedCats.map((c) => matrix[c]?.[m] ?? 0), 1);
  const currentMonth = new Date().toISOString().slice(0, 7);

  if (!months.length || !sortedCats.length)
    return <p className="py-8 text-center text-sm text-muted">Sin datos</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="table-head">
          <tr>
            <th className="px-4 py-3 whitespace-nowrap">Categoría</th>
            {months.map((m) => {
              const [y, mo] = m.split("-");
              return (
                <th key={m} className={`px-4 py-3 text-right whitespace-nowrap ${m === currentMonth ? "text-primary" : ""}`}>
                  {MONTH_NAMES[mo]} {y.slice(2)}
                  {m === currentMonth && <span className="ml-1 text-[9px] text-primary">●</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50 bg-card">
          {sortedCats.map((cat) => (
            <tr key={cat} className="hover:bg-slate-700/30">
              <td className="px-4 py-2.5 font-medium text-slate-200 whitespace-nowrap">{cat}</td>
              {months.map((m) => {
                const val       = matrix[cat]?.[m] ?? 0;
                const intensity = val > 0 ? Math.round((val / colMax[m]) * 80) + 10 : 0;
                return (
                  <td key={m} className="px-4 py-2.5 text-right">
                    {val > 0 ? (
                      <span
                        className="inline-block rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: `rgba(59, 130, 246, ${intensity / 100})`,
                          color: intensity > 50 ? "#fff" : "#94a3b8",
                        }}
                      >
                        {mxn(val)}
                      </span>
                    ) : (
                      <span className="text-border">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-900/30">
          <tr>
            <td className="px-4 py-2.5 text-xs font-semibold text-muted">Total mes</td>
            {months.map((m) => {
              const total = sortedCats.reduce((s, c) => s + (matrix[c]?.[m] ?? 0), 0);
              return (
                <td key={m} className={`px-4 py-2.5 text-right text-xs font-bold ${m === currentMonth ? "text-primary" : "text-slate-300"}`}>
                  {mxn(total)}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
      {hasMore && <p className="mt-2 pr-2 text-right text-[11px] text-muted">Últimos 6 meses · {allMonths.length} en total</p>}
    </div>
  );
}
