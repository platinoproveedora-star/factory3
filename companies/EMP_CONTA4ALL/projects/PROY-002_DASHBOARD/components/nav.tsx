"use client";
import { useEffect, useState } from "react";
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
const MODULE_CODE = "conta4all";

type CompanyOption = {
  company_id: string;
  name?: string;
};

export default function Nav({ email }: { email: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");

  useEffect(() => {
    fetch("/api/auth/grants/me")
      .then((res) => res.json())
      .then((json) => {
        const grants = Array.isArray(json.grants) ? json.grants : [];
        const allowedCompanyIds = new Set(
          grants
            .filter((grant: any) => grant.modulo_code === MODULE_CODE)
            .map((grant: any) => String(grant.company_id || ""))
            .filter(Boolean)
        );
        const rows = (Array.isArray(json.companies) ? json.companies : []).filter((company: CompanyOption) =>
          allowedCompanyIds.has(company.company_id)
        );
        setCompanies(rows);
        const stored = window.localStorage.getItem("conta4all_company_id") || "";
        const current =
          rows.find((company: CompanyOption) => company.company_id === stored)?.company_id ||
          rows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
          rows[0]?.company_id ||
          "";
        setSelectedCompanyId(current);
      })
      .catch(() => null);
  }, []);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push(portalUrl || "/login");
  }

  function selectCompany(companyId: string) {
    setSelectedCompanyId(companyId);
    window.localStorage.setItem("conta4all_company_id", companyId);
  }

  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
        <div className="flex items-center gap-1">
          <span className="font-bold text-white mr-4">Conta4all</span>
          {companies.length > 1 ? (
            <select
              value={selectedCompanyId}
              onChange={(event) => selectCompany(event.target.value)}
              className="mr-3 rounded-md border border-border bg-bg px-2 py-1 text-xs text-slate-100 outline-none focus:border-primary"
            >
              {companies.map((company) => (
                <option key={company.company_id} value={company.company_id}>
                  {company.name || company.company_id}
                </option>
              ))}
            </select>
          ) : null}
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
