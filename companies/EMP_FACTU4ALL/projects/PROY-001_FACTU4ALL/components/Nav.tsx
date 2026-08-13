import Link from "next/link";

export default function Nav({ active }: { active: string }) {
  const items = [
    { href: "/dashboard", label: "Inicio", key: "dashboard" },
    { href: "/invoices/new", label: "Nueva factura", key: "new" },
    { href: "/invoices", label: "Facturas emitidas", key: "invoices" },
    { href: "/settings", label: "Configuración", key: "settings" },
  ];
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl gap-1 px-5 py-3">
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
    </nav>
  );
}
