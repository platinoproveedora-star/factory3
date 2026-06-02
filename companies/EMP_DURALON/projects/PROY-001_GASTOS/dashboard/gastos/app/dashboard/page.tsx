import { Suspense } from 'react';
import { getStats, getGastos, type Gasto, type StatCategoria } from '../../lib/db';
import KpiGrid              from '../../components/KpiGrid';
import CategoryTable        from '../../components/CategoryTable';
import MonthlyTable         from '../../components/MonthlyTable';
import CategoryMonthlyTable from '../../components/CategoryMonthlyTable';
import ExpenseTable         from '../../components/ExpenseTable';

export const dynamic = 'force-dynamic';

function catsByMonth(gastos: Gasto[], month: string): { cats: StatCategoria[]; total: number } {
  const filtered = gastos.filter(g => g.fecha.startsWith(month));
  const map: Record<string, { total: number; count: number }> = {};
  for (const g of filtered) {
    const c = g.categoria || 'Sin categoría';
    if (!map[c]) map[c] = { total: 0, count: 0 };
    map[c].total += g.monto;
    map[c].count += 1;
  }
  const cats = Object.entries(map)
    .map(([categoria, v]) => ({ categoria, total: Math.round(v.total * 100) / 100, count: v.count }))
    .sort((a, b) => b.total - a.total);
  const total = cats.reduce((s, c) => s + c.total, 0);
  return { cats, total };
}

async function getData() {
  try {
    const [stats, gastos] = await Promise.all([getStats(), getGastos(500)]);
    return { stats, gastos, error: null };
  } catch (e: any) {
    return {
      stats: { total: 0, count: 0, avg: 0, totalMes: 0, totalMesAnt: 0, variacion: 0, por_categoria: [] },
      gastos: [],
      error: e?.message ?? 'Error al cargar datos',
    };
  }
}

export default async function DashboardPage() {
  const { stats, gastos, error } = await getData();

  const today       = new Date();
  const currentMonth = today.toISOString().slice(0, 7);
  const prevDate     = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const prevMonth    = prevDate.toISOString().slice(0, 7);
  const prevLabel    = prevDate.toLocaleString('es-MX', { month: 'long', year: 'numeric' });

  const { cats: catsMes, total: totalMes }       = catsByMonth(gastos, currentMonth);
  const { cats: catsMesAnt, total: totalMesAnt } = catsByMonth(gastos, prevMonth);

  return (
    <main className="flex min-h-screen bg-slate-50">

      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-56 border-r border-slate-200 bg-white px-5 py-6 z-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Factory3</p>
        <h1 className="mt-1 text-base font-semibold text-slate-900">Duralon Gastos</h1>
        <p className="mt-0.5 text-[11px] text-slate-400">EMP_DURALON · uc101_proy001</p>
        <nav className="mt-8 space-y-1 text-sm">
          <a href="#overview" className="block rounded-lg bg-slate-100 px-3 py-2 font-medium text-slate-900">
            📊 Overview
          </a>
          <a href="#gastos" className="block rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-50 hover:text-slate-900">
            📋 Gastos
          </a>
        </nav>
        <div className="absolute bottom-6 left-5 right-5">
          <p className="text-[10px] text-slate-400">{gastos.length} registros cargados</p>
        </div>
      </aside>

      {/* Main content */}
      <section className="ml-56 flex-1 px-8 py-6">

        {/* Header */}
        <div id="overview" className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide">Dashboard operativo</p>
            <h2 className="text-2xl font-semibold text-slate-900 mt-0.5">Overview</h2>
          </div>
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* KPIs — mes actual, compactos */}
        <KpiGrid
          gastos={gastos}
          variacion={stats.variacion ?? 0}
          totalMesAnt={stats.totalMesAnt ?? 0}
        />

        {/* Categorías mes actual + mes anterior */}
        <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Gastos por categoría — mes actual
            </h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
              <CategoryTable categorias={catsMes} total={totalMes} />
            </Suspense>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Gastos por categoría — <span className="text-slate-400">{prevLabel}</span>
            </h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
              <CategoryTable categorias={catsMesAnt} total={totalMesAnt} />
            </Suspense>
          </div>

        </div>

        {/* Comparativo mensual */}
        <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Comparativo mensual</h3>
          <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
            <MonthlyTable gastos={gastos} />
          </Suspense>
        </div>

        {/* Comparativo por categoría y mes */}
        <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Comparativo por categoría y mes</h3>
          <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
            <CategoryMonthlyTable gastos={gastos} />
          </Suspense>
        </div>

        {/* Tabla de movimientos */}
        <div id="gastos" className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Movimientos</h3>
          <Suspense fallback={<div className="h-64 animate-pulse rounded bg-slate-100" />}>
            <ExpenseTable gastos={gastos} />
          </Suspense>
        </div>

        <p className="mt-6 text-center text-[10px] text-slate-400">
          Factory3 · {new Date().toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })}
        </p>

      </section>
    </main>
  );
}
