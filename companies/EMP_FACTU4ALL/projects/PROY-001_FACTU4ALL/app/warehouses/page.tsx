import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import WarehousesForm from "./WarehousesForm";

export default async function WarehousesPage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="warehouses" />
      <div className="mx-auto max-w-3xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Almacenes</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            El inventario se lleva por almacén — cada empresa arranca con uno ("Principal"), puedes agregar más.
          </p>
        </section>
        <WarehousesForm />
      </div>
    </div>
  );
}
