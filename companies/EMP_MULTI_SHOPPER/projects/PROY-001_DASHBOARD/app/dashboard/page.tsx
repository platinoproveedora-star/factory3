import Link from "next/link";
import EmptyState from "@/components/empty-state";
import KpiGrid from "@/components/kpi-grid";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { fmtDate, getDashboardData, mxn } from "@/lib/data";

export default async function DashboardPage() {
  const { data, warning } = await getDashboardData();

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Cotizaciones, proveedores, documentos y precios"
        action={<Link href="/dashboard/sales-quotes" className="btn-primary">Nueva cotizacion</Link>}
      />
      {warning && <div className="card mb-4 border-yellow-800 bg-yellow-900/20 text-sm text-yellow-300">{warning}</div>}
      <KpiGrid data={data} />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <section className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Cotizaciones recientes</h2>
            <Link href="/dashboard/sales-quotes" className="text-sm text-primary hover:text-blue-300">Ver todas</Link>
          </div>
          {data.sales_quotes.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="table-head">
                  <tr><th className="px-3 py-2">Folio</th><th>Cliente</th><th>Estado</th><th>Fecha</th></tr>
                </thead>
                <tbody>
                  {data.sales_quotes.slice(0, 6).map((row) => (
                    <tr key={row.id}>
                      <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                      <td className="table-cell">{row.customer_name}</td>
                      <td className="table-cell"><StatusBadge value={row.status} /></td>
                      <td className="table-cell text-muted">{fmtDate(row.quote_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <EmptyState label="Sin cotizaciones" />}
        </section>

        <section className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Ultimos precios</h2>
            <Link href="/dashboard/products" className="text-sm text-primary hover:text-blue-300">Ver productos</Link>
          </div>
          {data.price_history.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead className="table-head">
                  <tr><th className="px-3 py-2">Producto</th><th>Proveedor</th><th>Precio</th><th>Fecha</th></tr>
                </thead>
                <tbody>
                  {data.price_history.slice(0, 6).map((row) => (
                    <tr key={row.id}>
                      <td className="table-cell">{row.product_name || "-"}</td>
                      <td className="table-cell">{row.supplier_name || "-"}</td>
                      <td className="table-cell font-semibold">{mxn(row.unit_price, row.currency || "MXN")}</td>
                      <td className="table-cell text-muted">{fmtDate(row.price_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <EmptyState label="Sin precios historicos" />}
        </section>
      </div>
    </div>
  );
}
