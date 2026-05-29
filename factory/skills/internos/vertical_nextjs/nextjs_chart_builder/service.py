from __future__ import annotations

from pathlib import Path


class NextjsChartBuilderService:
    def ejecutar(self, context: dict) -> dict:
        out_dir = Path(context.get("output_dir") or ".")
        files = {"components/ExpenseCharts.tsx": self._component()}
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"files": sorted(files.keys()), "output_dir": str(out_dir)}}

    def _component(self) -> str:
        return """"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const sample = [
  { name: 'Combustible', total: 36700 },
  { name: 'Taller', total: 15259.57 },
  { name: 'Nomina', total: 41684 },
];

export function ExpenseCharts() {
  return (
    <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-slate-950">Gasto por categoria</h2>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sample}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="total" fill="#0f172a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-slate-950">Tendencia diaria</h2>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sample}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line dataKey="total" stroke="#2563eb" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
"""

