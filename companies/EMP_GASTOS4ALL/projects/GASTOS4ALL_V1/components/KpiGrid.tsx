"use client";

import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { Gasto } from "@/lib/db";

type Props = { gastos: Gasto[]; variacion: number; totalMesAnt: number };

function mxn(n: number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
}

function VariIcon({ v }: { v: number }) {
  if (v > 1)  return <TrendingUp  size={13} className="text-red-400" />;
  if (v < -1) return <TrendingDown size={13} className="text-emerald-400" />;
  return <Minus size={13} className="text-muted" />;
}

export default function KpiGrid({ gastos, variacion, totalMesAnt }: Props) {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const mesNombre    = new Date().toLocaleString("es-MX", { month: "long", year: "numeric" });
  const mesGastos    = gastos.filter((g) => g.fecha.startsWith(currentMonth));
  const total        = mesGastos.reduce((s, g) => s + g.monto, 0);
  const count        = mesGastos.length;
  const avg          = count > 0 ? total / count : 0;

  const byCat: Record<string, number> = {};
  for (const g of mesGastos) byCat[g.categoria] = (byCat[g.categoria] ?? 0) + g.monto;
  const topCat = Object.entries(byCat).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  const varSign  = variacion >= 0 ? "+" : "";
  const varColor = variacion > 5 ? "text-red-400" : variacion < -5 ? "text-emerald-400" : "text-muted";

  const cards = [
    {
      label: mesNombre,
      value: mxn(total),
      sub: totalMesAnt > 0
        ? <span className="flex items-center gap-1">{varSign}{variacion.toFixed(1)}% vs mes ant <VariIcon v={variacion} /></span>
        : <span className="text-muted">primer mes</span>,
    },
    { label: "Movimientos", value: String(count), sub: "este mes" },
    { label: "Promedio",    value: mxn(avg),      sub: "por gasto este mes" },
    { label: "Mayor categoría", value: topCat,    sub: "este mes", mono: true },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="card">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">{c.label}</p>
          <p className={`mt-1 font-semibold text-white ${c.mono ? "text-sm" : "text-xl"}`}>{c.value}</p>
          <p className={`mt-0.5 text-[11px] ${varColor}`}>{c.sub}</p>
        </div>
      ))}
    </div>
  );
}
