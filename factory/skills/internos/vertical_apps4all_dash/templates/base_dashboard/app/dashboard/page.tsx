import { getSession } from "@/lib/auth";

export default async function DashboardPage() {
  const user = await getSession();
  if (!user) return null;

  return (
    <div className="mx-auto max-w-7xl px-5 py-6">
      <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Apps4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Bienvenido, {user.email}</h1>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-600">Empresa: {user.company_name || user.company_id}</p>
      </section>
      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">
          Home generico del modulo. Reemplazar con la pantalla real de este modulo Apps4All.
        </p>
      </div>
    </div>
  );
}
