from __future__ import annotations

from pathlib import Path


class NextjsTableBuilderService:
    def ejecutar(self, context: dict) -> dict:
        out_dir = Path(context.get("output_dir") or ".")
        files = {"components/ExpenseTable.tsx": self._component()}
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"files": sorted(files.keys()), "output_dir": str(out_dir)}}

    def _component(self) -> str:
        return """"use client";

import { useMemo, useState } from 'react';
import { downloadCsv } from '@/lib/export';

const rows = [
  { folio: 'GAS-001', fecha: '2026-05-02', categoria: 'combustible', monto: 1000, descripcion: 'DIESEL TORTON RETIRAR CAL' },
];

export function ExpenseTable() {
  const [search, setSearch] = useState('');
  const filtered = useMemo(() => rows.filter((row) => JSON.stringify(row).toLowerCase().includes(search.toLowerCase())), [search]);
  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-950">Detalle de gastos</h2>
        <div className="flex gap-2">
          <input className="rounded-md border border-slate-200 px-3 py-2 text-sm" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar" />
          <button className="rounded-md bg-slate-950 px-3 py-2 text-sm text-white" onClick={() => downloadCsv('gastos.csv', filtered)}>Exportar CSV</button>
        </div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-slate-500">
            <tr><th className="py-2">Folio</th><th>Fecha</th><th>Categoria</th><th>Monto</th><th>Descripcion</th></tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.folio} className="border-b border-slate-100">
                <td className="py-2 font-medium">{row.folio}</td><td>{row.fecha}</td><td>{row.categoria}</td><td>${row.monto.toLocaleString()}</td><td>{row.descripcion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
"""

