"use client";

import type { StatCategoria } from "@/lib/db";

type Props = { categorias: StatCategoria[]; total: number };

function mxn(n: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
}

export default function CategoryTable({ categorias, total }: Props) {
  if (!categorias.length) {
    return <p className="py-8 text-center text-sm text-muted">Sin datos por categoría</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="table-head">
          <tr>
            {["Categoría", "Total", "Movs", "% del total"].map((h) => (
              <th key={h} className="px-4 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50 bg-card">
          {categorias.map((c, i) => {
            const pct = total > 0 ? Math.round((c.total / total) * 100) : 0;
            return (
              <tr key={c.categoria} className="hover:bg-slate-700/30">
                <td className="px-4 py-2.5 font-medium text-slate-200">
                  <span className="mr-2 text-xs text-muted">#{i + 1}</span>
                  {c.categoria}
                </td>
                <td className="px-4 py-2.5 font-semibold text-white">{mxn(c.total)}</td>
                <td className="px-4 py-2.5 text-muted">{c.count}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-700">
                      <div className="h-1.5 rounded-full bg-primary" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-muted">{pct}%</span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot className="bg-slate-900/30">
          <tr>
            <td className="px-4 py-2.5 text-xs font-semibold text-muted">Total</td>
            <td className="px-4 py-2.5 font-bold text-white">{mxn(total)}</td>
            <td className="px-4 py-2.5 text-xs text-muted">
              {categorias.reduce((s, c) => s + c.count, 0)} movs
            </td>
            <td className="px-4 py-2.5 text-xs text-muted">100%</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
