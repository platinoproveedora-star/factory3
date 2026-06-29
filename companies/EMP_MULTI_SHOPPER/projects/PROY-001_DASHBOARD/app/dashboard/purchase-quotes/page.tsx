import EmptyState from "@/components/empty-state";
import { PurchaseQuoteCreateForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { fmtDate, getDashboardData } from "@/lib/data";

export default async function PurchaseQuotesPage() {
  const { data } = await getDashboardData();
  return (
    <div>
      <PageHeader title="Cotizaciones compra" subtitle="Solicitudes listas para WhatsApp o correo" />
      <PurchaseQuoteCreateForm suppliers={data.suppliers} salesQuotes={data.sales_quotes} />
      {data.purchase_quotes.length ? (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="table-head">
              <tr><th className="px-3 py-2">Folio</th><th>Proveedor</th><th>Cotizacion venta</th><th>Canal</th><th>Estado</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              {data.purchase_quotes.map((row) => (
                <tr key={row.id}>
                  <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                  <td className="table-cell">{row.supplier_name || "-"}</td>
                  <td className="table-cell">{row.sales_quote_folio || "-"}</td>
                  <td className="table-cell">{row.channel || "-"}</td>
                  <td className="table-cell"><StatusBadge value={row.status} /></td>
                  <td className="table-cell text-muted">{fmtDate(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Sin cotizaciones de compra" />}
    </div>
  );
}
