"use client";

import clsx from "clsx";
import {
  FilePlus,
  FileText,
  LayoutDashboard,
  LogOut,
  Package,
  Settings,
  ShoppingCart,
  Store,
  Truck,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/sales-quotes", label: "Venta", icon: FileText },
  { href: "/dashboard/products", label: "Productos", icon: Package },
  { href: "/dashboard/suppliers", label: "Proveedores", icon: Store },
  { href: "/dashboard/purchase-quotes", label: "Compra", icon: ShoppingCart },
  { href: "/dashboard/documents/add", label: "Add docs", icon: FilePlus },
  { href: "/dashboard/documents", label: "Docs", icon: Truck },
  { href: "/dashboard/settings", label: "Config", icon: Settings },
];

export default function Nav({ email }: { email: string }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
  }

  return (
    <nav className="sticky top-0 z-10 border-b border-border bg-card/50 backdrop-blur">
      <div className="mx-auto flex min-h-14 max-w-7xl flex-col gap-2 px-4 py-2 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-1 overflow-x-auto">
          <span className="mr-4 shrink-0 font-bold text-white">Multi Shopper</span>
          {links.map((link) => {
            const Icon = link.icon;
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                  active ? "bg-primary/20 text-primary" : "text-slate-400 hover:text-white"
                )}
                title={link.label}
              >
                <Icon size={15} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
        <div className="flex items-center justify-between gap-3 lg:justify-end">
          <span className="truncate text-sm text-muted">{email}</span>
          <button onClick={handleLogout} className="btn-ghost inline-flex items-center gap-1 py-1">
            <LogOut size={14} />
            Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
