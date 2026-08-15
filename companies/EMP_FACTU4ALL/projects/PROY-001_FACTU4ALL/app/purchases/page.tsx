import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import PurchasesForm from "./PurchasesForm";

export default async function PurchasesPage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="purchases" />
      <div className="mx-auto max-w-5xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Egresos — facturas de compra recibidas</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Sube el XML de una factura de proveedor. Se lee, se registra el proveedor y los productos, y cada
            concepto entra al kardex de inventario (existencia real, no simulada).
          </p>
        </section>
        <PurchasesForm />
      </div>
    </div>
  );
}
