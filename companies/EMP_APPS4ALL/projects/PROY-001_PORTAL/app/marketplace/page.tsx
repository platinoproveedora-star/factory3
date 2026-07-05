import { redirect } from "next/navigation";
import { ArrowUpRight, Boxes, CheckCircle2, CircleDollarSign, Store } from "lucide-react";
import { PortalShell } from "@/components/PortalShell";
import { getSession, getSessionToken } from "@/lib/auth";
import { callSkill } from "@/lib/factory";

export const dynamic = "force-dynamic";

type MarketplaceModule = {
  code: string;
  nombre?: string;
  description?: string;
  category?: string;
  marketplace_status?: string;
  activo?: boolean;
  app_url?: string;
  demo_url?: string;
  prod_url?: string;
  icon?: string;
  sort_order?: number;
  default_plan_code?: string;
  pricing_json?: unknown;
  tags?: string[];
};

type ModuleListPayload = {
  modules?: MarketplaceModule[];
  data?: {
    modules?: MarketplaceModule[];
  };
};

function modulesFromPayload(payload?: ModuleListPayload) {
  return payload?.modules || payload?.data?.modules || [];
}

function priceLabel(pricing: unknown) {
  if (!pricing || typeof pricing !== "object") return "Manual";
  const value = pricing as Record<string, unknown>;
  const currency = String(value.currency || "MXN");
  const amount = value.amount_monthly || value.monthly || value.price;
  if (!amount) return String(value.mode || "Manual");
  return `${currency} ${amount}/mes`;
}

function launchHref(module: MarketplaceModule, sessionToken: string | null) {
  const base = module.demo_url || module.prod_url || module.app_url || "";
  if (!base) return "#";
  if (!sessionToken) return base;
  return `${base}${base.includes("?") ? "&" : "?"}sso=${encodeURIComponent(sessionToken)}`;
}

export default async function MarketplacePage() {
  const user = await getSession();
  if (!user) redirect("/login");
  const sessionToken = await getSessionToken();
  const result = await callSkill<ModuleListPayload>("vertical_apps4all_marketplace/apps4all_marketplace_module_list", {
    status: "beta",
    active: true,
    limit: 100
  });
  const modules = result.ok ? modulesFromPayload(result.data) : [];

  return (
    <PortalShell user={user}>
      <section className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Marketplace</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Modulos listos para activar</h1>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
          <Store size={16} />
          <span>{modules.length} publicados</span>
        </div>
      </section>

      {!result.ok ? (
        <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          No se pudo leer Marketplace: {result.error || "error desconocido"}
        </section>
      ) : null}

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => {
          const href = launchHref(module, sessionToken);
          return (
            <article key={module.code} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-[#e4ece6] text-moss">
                  <Boxes size={20} />
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium uppercase text-slate-500">
                  <CheckCircle2 size={12} />
                  {module.marketplace_status || "draft"}
                </span>
              </div>
              <h2 className="mt-4 text-lg font-semibold text-ink">{module.nombre || module.code}</h2>
              <p className="mt-2 min-h-12 text-sm leading-6 text-slate-600">{module.description || "Modulo Apps4All."}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(module.tags || []).slice(0, 3).map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-500">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="mt-5 flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-1 text-sm font-medium text-slate-600">
                  <CircleDollarSign size={15} />
                  {priceLabel(module.pricing_json)}
                </span>
                <a
                  href={href}
                  target={href === "#" ? undefined : "_blank"}
                  rel={href === "#" ? undefined : "noreferrer"}
                  className="inline-flex items-center gap-1 rounded-md bg-ink px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
                >
                  Abrir
                  <ArrowUpRight size={15} />
                </a>
              </div>
            </article>
          );
        })}
      </section>

      {modules.length === 0 && result.ok ? (
        <section className="mt-6 rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Todavia no hay modulos publicados en Marketplace.
        </section>
      ) : null}
    </PortalShell>
  );
}
