import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import KardexTable from "./KardexTable";

export default async function KardexPage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="kardex" />
      <div className="mx-auto max-w-7xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Kardex fiscal</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Movimientos fiscales por CFDI — no controla inventario físico, solo qué se facturó por producto y por clave SAT.
          </p>
        </section>
        <KardexTable />
      </div>
    </div>
  );
}
