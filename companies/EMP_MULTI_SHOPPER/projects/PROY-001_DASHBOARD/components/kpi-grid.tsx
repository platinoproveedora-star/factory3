import { FileText, Package, ReceiptText, ShoppingCart, Store, Upload } from "lucide-react";
import type { DashboardData } from "@/lib/types";

export default function KpiGrid({ data }: { data: DashboardData }) {
  const rows = [
    { label: "Cotizaciones venta", value: data.kpis.active_sales_quotes, icon: FileText },
    { label: "Productos", value: data.kpis.products, icon: Package },
    { label: "Proveedores", value: data.kpis.suppliers, icon: Store },
    { label: "Cotizaciones compra", value: data.kpis.purchase_quotes, icon: ShoppingCart },
    { label: "Documentos", value: data.kpis.documents, icon: Upload },
    { label: "Precios historicos", value: data.kpis.price_records, icon: ReceiptText },
  ];
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
      {rows.map((row) => {
        const Icon = row.icon;
        return (
          <div className="card" key={row.label}>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm text-muted">{row.label}</p>
              <Icon size={17} className="text-primary" />
            </div>
            <p className="text-2xl font-bold">{row.value}</p>
          </div>
        );
      })}
    </div>
  );
}
