import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import ProductsForm from "./ProductsForm";

export default async function ProductsPage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="products" />
      <div className="mx-auto max-w-5xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Productos fiscales</h1>
        </section>
        <ProductsForm />
      </div>
    </div>
  );
}
