import EmptyState from "@/components/empty-state";
import { ProductCreateForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { getDashboardData } from "@/lib/data";

export default async function ProductsPage() {
  const { data } = await getDashboardData();
  return (
    <div>
      <PageHeader title="Productos" subtitle="Catalogo propio y referencias ERP opcionales" />
      <ProductCreateForm />
      {data.products.length ? (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="table-head">
              <tr><th className="px-3 py-2">Folio</th><th>Producto</th><th>Categoria</th><th>Unidad</th><th>Marca</th><th>ERP</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {data.products.map((row) => (
                <tr key={row.id}>
                  <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                  <td className="table-cell">{row.canonical_name}</td>
                  <td className="table-cell">{row.category_name || "-"}</td>
                  <td className="table-cell">{row.unit || "-"}</td>
                  <td className="table-cell">{row.brand || "-"}</td>
                  <td className="table-cell text-muted">{row.erp_product_id ? "linked" : "-"}</td>
                  <td className="table-cell"><StatusBadge value={row.status || "active"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Sin productos" />}
    </div>
  );
}
