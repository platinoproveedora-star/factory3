"use client";
import { useEffect, useState } from "react";
import { COMPANY_CHANGE_EVENT, COMPANY_STORAGE_KEY } from "@/components/nav";

const MODULE_CODE = "fleet4all";

export type CompanyOption = { company_id: string; name?: string };

function fleetCompanies(json: any): CompanyOption[] {
  const grants = Array.isArray(json.grants) ? json.grants : [];
  const allowedCompanyIds: string[] = Array.from(
    new Set(
      grants
        .filter((grant: any) => grant.modulo_code === MODULE_CODE)
        .map((grant: any) => String(grant.company_id || ""))
        .filter(Boolean)
    )
  );
  const companiesById = new Map<string, CompanyOption>(
    (Array.isArray(json.companies) ? json.companies : []).map((company: CompanyOption) => [company.company_id, company])
  );
  return allowedCompanyIds.map((companyId) => companiesById.get(companyId) || { company_id: companyId });
}

export function useCompany() {
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/auth/grants/me")
      .then((res) => res.json())
      .then((json) => {
        const rows = fleetCompanies(json);
        setCompanies(rows);
        const stored = window.localStorage.getItem(COMPANY_STORAGE_KEY) || "";
        const current =
          rows.find((company: CompanyOption) => company.company_id === stored)?.company_id ||
          rows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
          rows[0]?.company_id ||
          "";
        setSelectedCompanyId(current);
        if (current) window.localStorage.setItem(COMPANY_STORAGE_KEY, current);
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
