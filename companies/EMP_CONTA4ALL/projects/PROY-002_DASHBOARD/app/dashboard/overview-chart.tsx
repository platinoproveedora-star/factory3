"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface Cfdi {
  fecha?: string;
  fecha_emision?: string;
  tipo?: string;
  total?: number | string;
}

function buildChartData(cfdis: Cfdi[]) {
  const byMonth: Record<string, { mes: string; Ingresos: number; Egresos: number }> = {};
  for (const c of cfdis) {
    const fecha = c.fecha_emision || c.fecha;
    if (!fecha) continue;
    const mes = fecha.slice(0, 7);
    if (!byMonth[mes]) byMonth[mes] = { mes, Ingresos: 0, Egresos: 0 };
    const total = Number(c.total) || 0;
    if (c.tipo === "E") byMonth[mes].Ingresos += total;
    else if (c.tipo === "R") byMonth[mes].Egresos += total;
  }
  return Object.values(byMonth).sort((a, b) => a.mes.localeCompare(b.mes));
}

export default function OverviewChart({ cfdis }: { cfdis: Cfdi[] }) {
  const data = buildChartData(cfdis);
  if (data.length === 0) {
    return <p className="text-muted text-sm text-center py-8">Sin datos para graficar</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 16 }}>
        <XAxis dataKey="mes" tick={{ fill: "#64748b", fontSize: 12 }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          labelStyle={{ color: "#f1f5f9" }}
          formatter={(v: number) => v.toLocaleString("es-MX", { style: "currency", currency: "MXN" })}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Ingresos" fill="#22c55e" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Egresos" fill="#ef4444" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
