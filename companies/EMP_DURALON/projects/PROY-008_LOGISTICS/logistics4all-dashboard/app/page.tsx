import { redirect } from "next/navigation";
import { ArrowLeft, LogOut } from "lucide-react";
import { getSession } from "@/lib/auth";
import { loadLogisticsData } from "@/lib/logistics";
import { companyName, isPlatformAdmin, listCompanies, listGrants, logisticsGrants } from "@/lib/platform";
import { LogisticsDashboard } from "@/components/LogisticsDashboard";
import { CompanySelector } from "@/components/CompanySelector";

export const dynamic = "force-dynamic";

export default async function HomePage({ searchParams }: { searchParams?: Promise<{ company_id?: string }> }) {
  const user = await getSession();
  if (!user) redirect("/login");
  const params = (await searchParams) || {};
  const allGrants = await listGrants(user.sub);
  const grants = logisticsGrants(allGrants);
  if (!grants.length) redirect("/login");
  const logisticsCompanyIds = Array.from(new Set(grants.filter((grant) => grant.modulo_code === "logistics").map((grant) => grant.company_id)));
  const selectableCompanyIds = logisticsCompanyIds.length ? logisticsCompanyIds : Array.from(new Set(grants.map((grant) => grant.company_id)));
  const companies = await listCompanies(selectableCompanyIds);
  const selectedCompanyId = params.company_id || user.company_id;
  const allowed = selectableCompanyIds.includes(selectedCompanyId) || (isPlatformAdmin(grants) && selectableCompanyIds.length === 0);
  const companyId = allowed ? selectedCompanyId : selectableCompanyIds[0] || grants[0].company_id;
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
          <CompanySelector companies={companies} companyId={companyId} />
          <form action="/api/auth/logout" method="post">
            <button className="btn-soft min-h-10 px-3" title="Salir">
              <LogOut size={17} />
            </button>
          </form>
        </div>
        <CompanySelector companies={companies} companyId={companyId} mobile />
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
