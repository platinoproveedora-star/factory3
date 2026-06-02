import type { KardexMovement, Party, Product } from './supabase';

export type DashboardData = {
  products: Product[];
  customers: Party[];
  suppliers: Party[];
  purchases: KardexMovement[];
  sales: KardexMovement[];
  adjustments: KardexMovement[];
  stock: Array<{ product_id: string; product_name: string; quantity: number; total_in: number; total_out: number }>;
  receivables_total: number;
  payables_total: number;
};

export async function loadDashboardData(): Promise<DashboardData> {
  const res = await fetch('/api/summary', { cache: 'no-store' });
  const json = await res.json();
  if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudieron cargar datos');
  return json.data;
}
