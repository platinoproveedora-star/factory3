import EmptyState from "@/components/empty-state";
import { SalesQuoteCreateForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { fmtDate, getDashboardData } from "@/lib/data";

export default async function SalesQuotesPage() {
  const { data } = await getDashboardData();
  return (
    <div>
      <PageHeader title="Cotizaciones de venta" subtitle="Solicitudes internas y productos por cotizar" />
      <SalesQuoteCreateForm />
      {data.sales_quotes.length ? (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="table-head">
              <tr><th className="px-3 py-2">Folio</th><th>Cliente</th><th>Proyecto</th><th>Items</th><th>Estado</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              {data.sales_quotes.map((row) => (
                <tr key={row.id}>
                  <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                  <td className="table-cell">{row.customer_name}</td>
                  <td className="table-cell">{row.project_name || "-"}</td>
                  <td className="table-cell">{row.total_items || 0}</td>
                  <td className="table-cell"><StatusBadge value={row.status} /></td>
                  <td className="table-cell text-muted">{fmtDate(row.quote_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Sin cotizaciones de venta" />}
    </div>
  );
}
