import { DashboardData, emptyDashboardData } from "@/lib/types";
import { baseContext, dataSkill } from "@/lib/factory";

const DATA_SKILL = "vertical_multi_shopper/multi_shopper_dashboard_data";

export async function getDashboardData(): Promise<{ data: DashboardData; warning?: string }> {
  const result = await dataSkill<DashboardData>(DATA_SKILL, baseContext());
  if (!result.ok) return { data: emptyDashboardData, warning: result.error };
  return { data: result.data || emptyDashboardData };
}

export function mxn(value: number | null | undefined, currency = "MXN") {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

export function fmtDate(value?: string | null) {
  if (!value) return "-";
  return value.slice(0, 10);
}
