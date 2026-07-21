import { redirect } from "next/navigation";
import { ArrowLeft, LogOut } from "lucide-react";
import { getSession } from "@/lib/auth";
import { loadLogisticsData } from "@/lib/logistics";
import { companyName, isPlatformAdmin, listCompanies, listGrants, logisticsGrants } from "@/lib/platform";
import { LogisticsDashboard } from "@/components/LogisticsDashboard";

export const dynamic = "force-dynamic";

export default async function HomePage({ searchParams }: { searchParams?: Promise<{ company_id?: string }> }) {
  const user = await getSession();
  if (!user) redirect("/login");
  const params = (await searchParams) || {};
  const grants = logisticsGrants(await listGrants(user.sub));
  if (!grants.length) redirect("/login");
  const companies = await listCompanies(Array.from(new Set(grants.map((grant) => grant.company_id))));
  const selectedCompanyId = params.company_id || user.company_id;
  const allowed = isPlatformAdmin(grants) || grants.some((grant) => grant.company_id === selectedCompanyId);
  const companyId = allowed ? selectedCompanyId : grants[0].company_id;
  const dataResult = await loadLogisticsData(user, grants, companyId);
  const portalUrl = process.env.NEXT_PUBLIC_APPS4ALL_PORTAL_URL || "/";

  return (
    <main className="min-h-screen bg-paper">
      <header className="sticky top-0 z-30 border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-3 py-3 sm:px-5">
          <a href={portalUrl} className="btn-soft min-h-10 px-3" title="Apps4All">
            <ArrowLeft size={17} />
          </a>
          <div className="min-w-0 flex-1">
            <p className="text-lg font-semibold leading-tight text-ink">Logistics4All</p>
            <p className="truncate text-xs text-slate-500">{user.email}</p>
          </div>
          <form action="/" className="hidden sm:block">
            <select name="company_id" defaultValue={companyId} className="input w-52" aria-label="Empresa">
              {companies.map((company) => (
                <option key={company.company_id} value={company.company_id}>{company.name || company.company_id}</option>
              ))}
            </select>
          </form>
          <form action="/api/auth/logout" method="post">
            <button className="btn-soft min-h-10 px-3" title="Salir">
              <LogOut size={17} />
            </button>
          </form>
        </div>
        <form action="/" className="border-t border-line px-3 py-2 sm:hidden">
          <select name="company_id" defaultValue={companyId} className="input" aria-label="Empresa">
            {companies.map((company) => (
              <option key={company.company_id} value={company.company_id}>{company.name || company.company_id}</option>
            ))}
          </select>
        </form>
      </header>
      <LogisticsDashboard
        initialData={dataResult.ok ? dataResult.data || null : null}
        initialError={dataResult.ok ? "" : dataResult.error || "No se pudo cargar Logistics4All"}
        companyId={companyId}
        companyName={companyName(companies, companyId)}
      />
    </main>
  );
}
