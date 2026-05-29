from __future__ import annotations

from pathlib import Path


class NextjsModuleGeneratorService:
    def ejecutar(self, context: dict) -> dict:
        plan = context.get("dashboard_plan") or context.get("plan") or {}
        out_dir = Path(context.get("output_dir") or ".")
        files = {"app/dashboard/page.tsx": self._page(plan)}
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"files": sorted(files.keys()), "output_dir": str(out_dir)}}

    def _page(self, plan: dict) -> str:
        title = plan.get("project", {}).get("name", "Dashboard")
        return f"""import {{ ExpenseCharts }} from '@/components/ExpenseCharts';
import {{ ExpenseTable }} from '@/components/ExpenseTable';

export default function DashboardPage() {{
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500">Factory3 Dashboard</p>
            <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
          </div>
        </header>
        <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
          {{['Gasto total', 'Movimientos', 'Promedio', 'Categoria top'].map((label) => (
            <div key={{label}} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-sm text-slate-500">{{label}}</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">Pendiente</p>
            </div>
          ))}}
        </section>
        <ExpenseCharts />
        <ExpenseTable />
      </div>
    </main>
  );
}}
"""

