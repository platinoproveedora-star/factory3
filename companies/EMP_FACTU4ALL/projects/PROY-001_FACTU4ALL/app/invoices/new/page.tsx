import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import NewInvoiceForm from "./NewInvoiceForm";

export default async function NewInvoicePage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="new" />
      <div className="mx-auto max-w-4xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Nueva factura</h1>
        </section>
        <NewInvoiceForm />
      </div>
    </div>
  );
}
