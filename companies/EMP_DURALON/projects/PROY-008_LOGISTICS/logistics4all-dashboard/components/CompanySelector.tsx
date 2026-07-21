"use client";

import type { Company } from "@/lib/platform";

export function CompanySelector({ companies, companyId, mobile = false }: { companies: Company[]; companyId: string; mobile?: boolean }) {
  return (
    <form action="/" className={mobile ? "border-t border-line px-3 py-2 sm:hidden" : "hidden sm:block"}>
      <select
        name="company_id"
        defaultValue={companyId}
        className={mobile ? "input" : "input w-52"}
        aria-label="Empresa"
        onChange={(event) => event.currentTarget.form?.requestSubmit()}
      >
        {companies.map((company) => (
          <option key={company.company_id} value={company.company_id}>
            {company.name || company.company_id}
          </option>
        ))}
      </select>
    </form>
  );
}
