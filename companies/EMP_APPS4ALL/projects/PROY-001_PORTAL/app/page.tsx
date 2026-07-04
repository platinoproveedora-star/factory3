import { redirect } from "next/navigation";
import { ArrowUpRight, FileSpreadsheet, ReceiptText, ShoppingBasket } from "lucide-react";
import { getSession } from "@/lib/auth";
import { listCompanies, listGrants, companyName } from "@/lib/platform";
import { PortalShell } from "@/components/PortalShell";

export const dynamic = "force-dynamic";

const MODULES: Record<string, { title: string; description: string; href: string; icon: any; external?: boolean }> = {
  apps4all_portal: {
    title: "Apps4All",
    description: "Menu central, empresas y acceso.",
    href: "/",
    icon: ArrowUpRight
  },
  conta4all: {
    title: "Conta4All",
    description: "CFDI, RFCs administrados y sincronizacion SAT.",
    href: process.env.NEXT_PUBLIC_CONTA4ALL_URL || "#",
    icon: FileSpreadsheet,
    external: true
  },
  coti4all_portal: {
    title: "Coti4All",
    description: "Cotizador multiempresa, catalogo y documento para cliente.",
    href: process.env.NEXT_PUBLIC_COTI4ALL_URL || "#",
    icon: FileSpreadsheet,
    external: true
  },
  vertical_multi_shopper: {
    title: "Multi Shopper",
    description: "Cotizaciones, proveedores, productos y pricing.",
    href: process.env.NEXT_PUBLIC_MULTI_SHOPPER_URL || "#",
    icon: ShoppingBasket,
    external: true
  },
  gastos: {
    title: "Gastos",
    description: "Gastos operativos, KPIs, filtros y CSV.",
    href: "/apps/gastos",
    icon: ReceiptText
  }
};

export default async function HomePage() {
  const user = await getSession();
  if (!user) redirect("/login");
  const grants = await listGrants(user.sub);
  const companies = await listCompanies(Array.from(new Set(grants.map((grant) => grant.company_id))));
  const grantsByModule = Array.from(
    grants
      .reduce((map, grant) => {
        const rows = map.get(grant.modulo_code) || [];
        rows.push(grant);
        map.set(grant.modulo_code, rows);
        return map;
      }, new Map<string, typeof grants>())
      .entries()
  ).sort(([a], [b]) => a.localeCompare(b));

  return (
    <PortalShell user={user}>
      <section className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Portal central</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Tus modulos activos</h1>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-600">
          Contrato preparado para multiempresa y Stripe: company, rol, plan y estado de suscripcion viven en grants.
        </p>
      </section>
      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {grantsByModule.map(([moduloCode, moduleGrants]) => {
          const module = MODULES[moduloCode] || {
            title: moduloCode,
            description: "Modulo activo.",
            href: "#",
            icon: ArrowUpRight
          };
          const Icon = module.icon;
          const companyNames = moduleGrants.map((grant) => companyName(companies, grant.company_id));
          const roles = moduleGrants.map((grant) => grant.role);
          const role = roles.includes("platform_admin") ? "platform_admin" : roles.includes("owner") ? "owner" : roles[0] || "admin";
          const statuses = moduleGrants.map((grant) => grant.subscription_status || grant.status);
          const status = statuses.includes("active") ? "active" : statuses[0] || "manual";
          return (
            <a
              key={moduloCode}
              href={module.href}
              target={module.external ? "_blank" : undefined}
              rel={module.external ? "noreferrer" : undefined}
              className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-steel hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-[#e4ece6] text-moss">
                  <Icon size={20} />
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium uppercase text-slate-500">
                  {status}
                </span>
              </div>
              <h2 className="mt-4 text-lg font-semibold text-ink">{module.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
              <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-500">
                <span className="truncate">
                  {moduleGrants.length} {moduleGrants.length === 1 ? "empresa" : "empresas"}
                </span>
                <span>{role}</span>
              </div>
              <p className="mt-2 truncate text-xs text-slate-400" title={companyNames.join(", ")}>
                {companyNames.slice(0, 3).join(", ")}
                {companyNames.length > 3 ? ` +${companyNames.length - 3}` : ""}
              </p>
            </a>
          );
        })}
      </section>
    </PortalShell>
  );
}
