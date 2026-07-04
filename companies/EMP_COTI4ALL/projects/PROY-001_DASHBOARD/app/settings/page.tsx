import Link from "next/link";
import { getSession } from "@/lib/auth";

export default async function SettingsPage() {
  const user = await getSession();
  if (!user) return null;
  const portalHref = process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018";

  return (
    <div className="mx-auto max-w-7xl px-5 py-6">
      <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Configuración</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Ajustes del módulo</h1>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-600">Empresa seleccionada, grants, listas de precios y configuración general.</p>
      </section>
      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">Usuario activo: {user.email}</p>
        <p className="text-sm text-slate-500">Empresa: {user.company_name || user.company_id}</p>
        <p className="text-sm text-slate-500">Rol: {user.role}</p>
        <div className="mt-4 flex gap-2">
          <Link href={portalHref} className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:border-steel hover:text-steel">Portal Apps4All</Link>
          <Link href="/cotizador" className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:border-steel hover:text-steel">Cotizador</Link>
        </div>
      </div>
    </div>
  );
}
