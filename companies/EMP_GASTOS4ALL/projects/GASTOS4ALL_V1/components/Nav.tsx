"use client";

import { ArrowLeft, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Nav({
  email,
  empresa,
  companyOptions,
  selectedCompanyId
}: {
  email: string;
  empresa: string;
  companyOptions: Array<{ company_id: string; name: string }>;
  selectedCompanyId: string;
}) {
  const router = useRouter();
  const apps4allHref = process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018";

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push(apps4allHref);
  }

  return (
    <nav className="sticky top-0 z-10 border-b border-border bg-card/50 backdrop-blur">
      <div className="mx-auto flex min-h-14 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <a href={apps4allHref} className="btn-ghost inline-flex items-center gap-1 py-1 text-xs">
            <ArrowLeft size={13} /> Apps4All
          </a>
          <span className="font-bold text-white">Gastos4All</span>
          <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary">
            {empresa}
          </span>
          {companyOptions.length > 1 && (
            <select
              value={selectedCompanyId}
              onChange={(event) => router.push(`/dashboard?company_id=${encodeURIComponent(event.target.value)}`)}
              className="rounded-md border border-border bg-bg px-2 py-1 text-xs text-slate-100 outline-none focus:border-primary"
            >
              {companyOptions.map((company) => (
                <option key={company.company_id} value={company.company_id}>
                  {company.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">{email}</span>
          <button
            onClick={handleLogout}
            className="btn-ghost inline-flex items-center gap-1 py-1 text-xs"
          >
            <LogOut size={13} /> Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
