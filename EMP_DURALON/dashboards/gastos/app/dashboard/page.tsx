import { Suspense } from 'react';
import { getStats, getGastos } from '../../lib/db';
import KpiGrid       from '../../components/KpiGrid';
import CategoryTable from '../../components/CategoryTable';
import MonthlyTable  from '../../components/MonthlyTable';
import ExpenseTable  from '../../components/ExpenseTable';

export const dynamic = 'force-dynamic';

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
  const topCategoria = stats.por_categoria?.[0]?.categoria ?? '—';

  return (
    <main className="flex min-h-screen bg-slate-50">

      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-56 border-r border-slate-200 bg-white px-5 py-6 z-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Factory3</p>
        <h1 className="mt-1 text-base font-semibold text-slate-900">Duralon Gastos</h1>
        <p className="mt-0.5 text-[11px] text-slate-400">UC-101 · uc101_proy001</p>
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
        <div id="overview" className="flex items-start justify-between mb-6">
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

        {/* KPIs */}
        <Suspense fallback={<div className="h-28 animate-pulse rounded-xl bg-slate-100" />}>
          <KpiGrid
            total={stats.total}
            count={stats.count}
            avg={stats.avg}
            totalMes={stats.totalMes ?? 0}
            totalMesAnt={stats.totalMesAnt ?? 0}
            variacion={stats.variacion ?? 0}
            topCategoria={topCategoria}
          />
        </Suspense>

        {/* Tablas analíticas — dos columnas */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* Tabla por categoría */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Gasto por categoría</h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
              <CategoryTable
                categorias={stats.por_categoria ?? []}
                total={stats.total}
              />
            </Suspense>
          </div>

          {/* Tabla comparativo mensual */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Comparativo mensual</h3>
            <Suspense fallback={<div className="h-48 animate-pulse rounded bg-slate-100" />}>
              <MonthlyTable gastos={gastos} />
            </Suspense>
          </div>

        </div>

        {/* Tabla de movimientos */}
        <div id="gastos" className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Movimientos recientes</h3>
          <Suspense fallback={<div className="h-64 animate-pulse rounded bg-slate-100" />}>
            <ExpenseTable gastos={gastos} />
          </Suspense>
        </div>

        <p className="mt-8 text-center text-[10px] text-slate-400">
          Factory3 · {new Date().toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })}
        </p>

      </section>
    </main>
  );
}
