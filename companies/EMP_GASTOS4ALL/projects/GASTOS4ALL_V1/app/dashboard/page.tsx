import { Suspense } from "react";
import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import { calcStats, getGastos } from "@/lib/db";
import Nav                   from "@/components/Nav";
import KpiGrid               from "@/components/KpiGrid";
import CategoryTable         from "@/components/CategoryTable";
import MonthlyTable          from "@/components/MonthlyTable";
import CategoryMonthlyTable  from "@/components/CategoryMonthlyTable";
import ExpenseTable          from "@/components/ExpenseTable";

export const dynamic = "force-dynamic";

function catsByMonth(gastos: Awaited<ReturnType<typeof getGastos>>, month: string) {
  const filtered = gastos.filter((g) => g.fecha.startsWith(month));
  const map: Record<string, { total: number; count: number }> = {};
  for (const g of filtered) {
    const c = g.categoria || "Sin categoría";
    if (!map[c]) map[c] = { total: 0, count: 0 };
    map[c].total += g.monto;
    map[c].count += 1;
  }
  const cats = Object.entries(map)
    .map(([categoria, v]) => ({ categoria, total: Math.round(v.total * 100) / 100, count: v.count }))
    .sort((a, b) => b.total - a.total);
  return { cats, total: cats.reduce((s, c) => s + c.total, 0) };
}

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const empresaId = session.company_id;

  let stats:  ReturnType<typeof calcStats> | null = null;
  let gastos: Awaited<ReturnType<typeof getGastos>> = [];
  let loadError: string | null = null;

  try {
    gastos = await getGastos(empresaId, 2000);
    stats  = calcStats(gastos);
  } catch (e: any) {
    loadError = e?.message ?? "Error al cargar datos";
    stats = { total:0, count:0, avg:0, por_categoria:[], totalMes:0, totalMesAnt:0, variacion:0 };
  }

  const today        = new Date();
  const currentMonth = today.toISOString().slice(0, 7);
  const prevDate     = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const prevMonth    = prevDate.toISOString().slice(0, 7);
  const prevLabel    = prevDate.toLocaleString("es-MX", { month: "long", year: "numeric" });

  const { cats: catsMes,    total: totalMes }    = catsByMonth(gastos, currentMonth);
  const { cats: catsMesAnt, total: totalMesAnt } = catsByMonth(gastos, prevMonth);

  return (
    <div className="min-h-screen bg-bg">
      <Nav email={session.email} empresa={empresaId} />

      <main className="mx-auto max-w-7xl px-4 py-6 space-y-6">
        {loadError && (
          <div className="rounded-lg border border-red-800 bg-red-900/30 px-4 py-3 text-sm text-red-400">
            ⚠️ {loadError}
          </div>
        )}

        <KpiGrid gastos={gastos} variacion={stats?.variacion ?? 0} totalMesAnt={stats?.totalMesAnt ?? 0} />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">Categorías — mes actual</h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-800" />}>
              <CategoryTable categorias={catsMes} total={totalMes} />
            </Suspense>
          </div>
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">
              Categorías — <span className="text-muted">{prevLabel}</span>
            </h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-800" />}>
              <CategoryTable categorias={catsMesAnt} total={totalMesAnt} />
            </Suspense>
          </div>
        </div>

        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">Comparativo mensual</h3>
          <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-800" />}>
            <MonthlyTable gastos={gastos} />
          </Suspense>
        </div>

        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">Por categoría y mes</h3>
          <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-800" />}>
            <CategoryMonthlyTable gastos={gastos} />
          </Suspense>
        </div>

        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">Movimientos</h3>
          <Suspense fallback={<div className="h-64 animate-pulse rounded bg-slate-800" />}>
            <ExpenseTable gastos={gastos} bankAccounts={[]} empresaId={empresaId} />
          </Suspense>
        </div>

        <p className="text-center text-[10px] text-muted">
          Gastos4All · {new Date().toLocaleString("es-MX", { day:"2-digit", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit" })}
        </p>
      </main>
    </div>
  );
}
