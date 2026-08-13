import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import InvoiceList from "./InvoiceList";

export default async function InvoicesPage() {
  await requireModuleSession();

  return (
    <div>
      <Nav active="invoices" />
      <div className="mx-auto max-w-7xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Factu4All</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Facturas emitidas</h1>
        </section>
        <InvoiceList />
      </div>
    </div>
  );
}
