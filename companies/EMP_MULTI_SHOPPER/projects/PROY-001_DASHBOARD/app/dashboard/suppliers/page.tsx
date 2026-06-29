import EmptyState from "@/components/empty-state";
import { SupplierCreateForm } from "@/components/create-forms";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { getDashboardData } from "@/lib/data";

export default async function SuppliersPage() {
  const { data } = await getDashboardData();
  return (
    <div>
      <PageHeader title="Proveedores" subtitle="Contactos, categorias y cobertura" />
      <SupplierCreateForm />
      {data.suppliers.length ? (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="table-head">
              <tr><th className="px-3 py-2">Folio</th><th>Proveedor</th><th>Tipo</th><th>Ciudad</th><th>Categorias</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {data.suppliers.map((row) => (
                <tr key={row.id}>
                  <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                  <td className="table-cell">{row.name}</td>
                  <td className="table-cell">{row.supplier_type || "-"}</td>
                  <td className="table-cell">{[row.city, row.state].filter(Boolean).join(", ") || "-"}</td>
                  <td className="table-cell">{(row.categories || []).join(", ") || "-"}</td>
                  <td className="table-cell"><StatusBadge value={row.status || "active"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Sin proveedores" />}
    </div>
  );
}
