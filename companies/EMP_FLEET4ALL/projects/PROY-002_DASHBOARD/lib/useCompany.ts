"use client";
import { useEffect, useState } from "react";
import { COMPANY_CHANGE_EVENT, COMPANY_STORAGE_KEY } from "@/components/nav";

const MODULE_CODE = "fleet4all";

export type CompanyOption = { company_id: string; name?: string };

export function useCompany() {
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [loading, setLoading] = useState(true);

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
        const stored = window.localStorage.getItem(COMPANY_STORAGE_KEY) || "";
        const current =
          rows.find((company: CompanyOption) => company.company_id === stored)?.company_id ||
          rows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
          rows[0]?.company_id ||
          "";
        setSelectedCompanyId(current);
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onChange = (event: Event) => setSelectedCompanyId(String((event as CustomEvent).detail || ""));
    window.addEventListener(COMPANY_CHANGE_EVENT, onChange);
    return () => window.removeEventListener(COMPANY_CHANGE_EVENT, onChange);
  }, []);

  return { companies, selectedCompanyId, loading };
}
