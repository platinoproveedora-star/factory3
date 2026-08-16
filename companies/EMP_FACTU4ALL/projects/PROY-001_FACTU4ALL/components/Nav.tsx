import Link from "next/link";
import CompanySwitcher from "./CompanySwitcher";

export default function Nav({ active }: { active: string }) {
  const items = [
    { href: "/dashboard", label: "Inicio", key: "dashboard" },
    { href: "/invoices/new", label: "Nueva factura", key: "new" },
    { href: "/invoices", label: "Facturas emitidas", key: "invoices" },
    { href: "/purchases", label: "Egresos", key: "purchases" },
    { href: "/parties", label: "Clientes/Proveedores", key: "parties" },
    { href: "/products", label: "Productos fiscales", key: "products" },
    { href: "/warehouses", label: "Almacenes", key: "warehouses" },
    { href: "/kardex", label: "Kardex fiscal", key: "kardex" },
    { href: "/settings", label: "Configuración", key: "settings" },
  ];
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-5 py-3">
        <div className="flex flex-wrap gap-1">
          {items.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={
                "rounded-md px-3 py-2 text-sm font-semibold " +
                (active === item.key ? "bg-moss text-white" : "text-slate-600 hover:bg-slate-100")
              }
            >
              {item.label}
            </Link>
          ))}
        </div>
        <CompanySwitcher />
      </div>
    </nav>
  );
}
