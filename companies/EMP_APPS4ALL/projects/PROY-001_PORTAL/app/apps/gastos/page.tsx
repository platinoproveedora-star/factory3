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
  const gastosGrant = grants.find((grant) => grant.modulo_code === "gastos");
  if (!gastosGrant) {
    return (
      <PortalShell user={user}>
        <div className="rounded-lg border border-red-800 bg-red-900/30 p-5 text-red-400">
          No tienes acceso activo a Gastos.
        </div>
      </PortalShell>
    );
  }
  const companyId = gastosGrant.company_id;
  let gastos: Awaited<ReturnType<typeof listGastos>> = [];
  let categories: Awaited<ReturnType<typeof listCategories>> = [];
  let bankAccounts: Awaited<ReturnType<typeof listBankAccounts>> = [];
  let loadError: string | null = null;
  try {
    [gastos, categories, bankAccounts] = await Promise.all([
      listGastos(companyId),
      listCategories(companyId),
      listBankAccounts(companyId)
    ]);
  } catch (err: any) {
    loadError = err?.message || "Error cargando datos";
  }
  return (
    <PortalShell user={user}>
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <Link href="/" className="text-sm text-steel hover:underline">Volver al portal</Link>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Gastos</h1>
          <p className="mt-1 text-sm text-slate-400">Operacion diaria, filtros y captura rapida.</p>
        </div>
      </div>
      {loadError && (
        <div className="mb-4 rounded-lg border border-amber-700 bg-amber-900/30 px-4 py-3 text-sm text-amber-300">
          No se pudieron cargar los gastos: {loadError}
        </div>
      )}
      <GastosDashboard initialGastos={gastos} initialStats={summarize(gastos)} categories={categories.map((item) => item.nombre)} bankAccounts={bankAccounts} />
    </PortalShell>
  );
}
