import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import { listInvoices, listIssuerProfiles } from "@/lib/factu4all";

export default async function DashboardPage() {
  const user = await requireModuleSession();

  const [issuerRes, invoicesRes] = await Promise.all([
    listIssuerProfiles(user.company_id),
    listInvoices(user.company_id, "issued"),
  ]);
  const issuers = ((issuerRes.data as any)?.issuer_profiles || []) as any[];
  const invoices = ((invoicesRes.data as any)?.cfdi_documents || []) as any[];
  const stamped = invoices.filter((row) => row.status === "stamped");
  const drafts = invoices.filter((row) => row.status === "draft");
  const ready = issuers.some((row) => row.status === "ready");

  return (
    <div>
      <Nav active="dashboard" />
      <div className="mx-auto max-w-7xl px-5 py-6">
        <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Bienvenido, {user.email}</h1>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">Empresa: {user.company_name || user.company_id}</p>
        </section>

        {!ready && (
          <div className="mt-6 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
            Todavía no hay un emisor fiscal listo. Ve a{" "}
            <a href="/settings" className="font-semibold underline">
              Configuración
            </a>{" "}
            para capturar el RFC, régimen fiscal y credenciales del PAC antes de facturar.
          </div>
        )}

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="card">
            <p className="text-xs font-semibold uppercase text-slate-500">Facturas timbradas</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{stamped.length}</p>
          </div>
          <div className="card">
            <p className="text-xs font-semibold uppercase text-slate-500">Borradores</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{drafts.length}</p>
          </div>
          <div className="card">
            <p className="text-xs font-semibold uppercase text-slate-500">Emisores configurados</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{issuers.length}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
