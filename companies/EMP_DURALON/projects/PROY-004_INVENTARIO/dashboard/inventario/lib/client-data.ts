import type { KardexMovement, Party, Product } from './supabase';

export type DashboardData = {
  products: Product[];
  customers: Party[];
  suppliers: Party[];
  purchases: KardexMovement[];
  sales: KardexMovement[];
  adjustments: KardexMovement[];
  stock: Array<{
    product_id: string;
    folio?: string | null;
    product_key?: string | null;
    product_name: string;
    sku?: string | null;
    category?: string | null;
    category_2?: string | null;
    brand?: string | null;
    unit?: string | null;
    active?: boolean;
    is_key_product?: boolean;
    min_stock?: number;
    quantity: number;
    total_in: number;
    total_out: number;
    stock_delta?: number;
    stock_status?: string;
    avg_cost?: number;
    last_cost?: number;
    estimated_value?: number;
  }>;
  lot_stock?: Array<{
    product_id: string;
    lot_code: string;
    display_name: string;
    folio?: string | null;
    product_key?: string | null;
    product_name?: string | null;
    sku?: string | null;
    category?: string | null;
    category_2?: string | null;
    brand?: string | null;
    unit?: string | null;
    is_key_product?: boolean;
    quantity: number;
    total_in: number;
    total_out: number;
    lot_unit_cost?: number;
    avg_cost?: number;
    last_cost?: number;
    estimated_value?: number;
    first_movement_date?: string | null;
    last_movement_date?: string | null;
  }>;
  receivables_total: number;
  payables_total: number;
};

export async function loadDashboardData(): Promise<DashboardData> {
  const res = await fetch(`/api/summary?t=${Date.now()}`, { cache: 'no-store' });
  const json = await res.json();
  if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudieron cargar datos');
  return json.data;
}
