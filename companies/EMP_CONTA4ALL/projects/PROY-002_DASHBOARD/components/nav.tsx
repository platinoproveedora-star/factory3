"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/dashboard", label: "Resumen" },
  { href: "/dashboard/rfcs", label: "Mis RFCs" },
  { href: "/dashboard/sincronizar", label: "Sincronizar" },
  { href: "/dashboard/cfdis", label: "CFDIs" },
];

const portalUrl = process.env.NEXT_PUBLIC_APPS4ALL_URL || "";
export const COMPANY_CHANGE_EVENT = "conta4all:company-change";
export const COMPANY_STORAGE_KEY = "conta4all_company_id";

export default function Nav({ email }: { email: string }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push(portalUrl || "/login");
  }

  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
        <div className="flex items-center gap-1">
          <span className="font-bold text-white mr-4">Conta4all</span>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-sm transition-colors",
                pathname === l.href
                  ? "bg-primary/20 text-primary"
                  : "text-slate-400 hover:text-white"
              )}
            >
              {l.label}
            </Link>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {portalUrl ? (
            <a href={portalUrl} className="btn-ghost text-sm py-1">
              Apps4All
            </a>
          ) : null}
          <span className="text-muted text-sm hidden sm:block">{email}</span>
          <button onClick={handleLogout} className="btn-ghost text-sm py-1">
            Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
