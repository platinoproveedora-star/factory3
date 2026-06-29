import { redirect } from "next/navigation";
import Link from "next/link";
import { getSession } from "@/lib/auth";
import { listGrants } from "@/lib/platform";
import { listBankAccounts, listCategories, listGastos, summarize } from "@/lib/gastos";
import { PortalShell } from "@/components/PortalShell";
import { GastosDashboard } from "@/components/GastosDashboard";

export const dynamic = "force-dynamic";

export default async function GastosPage() {
  const user = await getSession();
  if (!user) redirect("/login");
  const grants = await listGrants(user.sub);
  const gastosCompanyId = process.env.GASTOS_COMPANY_ID;
  if (!gastosCompanyId) throw new Error("GASTOS_COMPANY_ID requerido");
  const hasAccess = grants.some((grant) => grant.company_id === gastosCompanyId && grant.modulo_code === "gastos");
  if (!hasAccess) {
    return (
      <PortalShell user={user}>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-900">
          No tienes acceso activo a Gastos.
        </div>
      </PortalShell>
    );
  }
  const [gastos, categories, bankAccounts] = await Promise.all([listGastos(), listCategories(), listBankAccounts()]);
  return (
    <PortalShell user={user}>
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <Link href="/" className="text-sm text-steel hover:underline">Volver al portal</Link>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Gastos</h1>
          <p className="mt-1 text-sm text-slate-600">Operacion diaria, filtros y captura rapida.</p>
        </div>
      </div>
      <GastosDashboard initialGastos={gastos} initialStats={summarize(gastos)} categories={categories.map((item) => item.nombre)} bankAccounts={bankAccounts} />
    </PortalShell>
  );
}
