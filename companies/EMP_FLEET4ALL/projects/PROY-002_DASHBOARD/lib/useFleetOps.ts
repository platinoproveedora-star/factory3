"use client";
import { useCallback, useEffect, useState } from "react";

export function useFleetOps(selectedCompanyId: string, sections: string[]) {
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reloadTick, setReloadTick] = useState(0);
  const sectionKey = sections.join(",");

  useEffect(() => {
    if (!selectedCompanyId || !sections.length) return;
    const qs = new URLSearchParams({
      empresa_id: selectedCompanyId,
      sections: sectionKey,
      limit: "200",
    });
    setLoading(true);
    setError("");
    fetch(`/api/operacion?${qs.toString()}`)
      .then((response) => response.json())
      .then((json) => {
        if (json.ok) setData(json.data || {});
        else setError(json.error || "No se pudieron cargar datos operativos");
      })
      .catch(() => setError("No se pudieron cargar datos operativos"))
      .finally(() => setLoading(false));
  }, [selectedCompanyId, sectionKey, sections.length, reloadTick]);

  const refetch = useCallback(() => setReloadTick((t) => t + 1), []);

  return { data, loading, error, refetch };
}
