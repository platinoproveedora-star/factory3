"use client";

import { useEffect, useState } from "react";

type Grant = { company_id: string; modulo_code: string };
type Company = { company_id: string; name: string };

export default function CompanySwitcher() {
  const [options, setOptions] = useState<Company[]>([]);
  const [currentCompanyId, setCurrentCompanyId] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/auth/grants/me");
      if (!res.ok) return;
      const data = await res.json();
      const grants: Grant[] = data.grants || [];
      const companies: Company[] = data.companies || [];
      const companyIds = Array.from(new Set(grants.filter((g) => g.modulo_code === "factu4all").map((g) => g.company_id)));
      setOptions(companyIds.map((id) => companies.find((c) => c.company_id === id) || { company_id: id, name: id }));
      setCurrentCompanyId(data.user?.company_id || "");
    })();
  }, []);

  async function handleChange(companyId: string) {
    if (!companyId || companyId === currentCompanyId) return;
    setBusy(true);
    const res = await fetch("/api/auth/switch-company", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: companyId }),
    });
    if (res.ok) {
      window.location.href = "/dashboard";
    } else {
      setBusy(false);
    }
  }

  if (options.length <= 1 || !currentCompanyId) return null;

  return (
    <select
      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
      value={currentCompanyId}
      disabled={busy}
      onChange={(e) => handleChange(e.target.value)}
    >
      {options.map((company) => (
        <option key={company.company_id} value={company.company_id}>
          {company.name}
        </option>
      ))}
    </select>
  );
}
