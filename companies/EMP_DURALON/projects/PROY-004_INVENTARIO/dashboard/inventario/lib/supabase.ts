import { createClient } from '@supabase/supabase-js';

const schema = process.env.SUPABASE_SCHEMA || 'uc101_proy004';

export function getSupabase() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error('Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY');
  }
  return createClient(url, key, {
    db: { schema },
    auth: { persistSession: false },
  });
}

export type Product = {
  id: string;
  folio: string;
  product_key: string | null;
  product_name: string;
  sku: string | null;
  category: string | null;
  category_2: string | null;
  brand: string | null;
  unit: string;
  active: boolean;
  is_key_product: boolean;
  min_stock: number;
};

export type Party = {
  id: string;
  folio: string;
  party_type: 'customer' | 'supplier' | 'both';
  party_name: string;
  legal_name: string | null;
  rfc: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  active: boolean;
};

export type KardexMovement = {
  id: string;
  folio: string;
  movement_type: 'entrada' | 'salida' | 'ajuste' | 'devolucion';
  source_type: 'compra' | 'remision' | 'ajuste' | 'devolucion';
  source_folio: string | null;
  external_folio: string | null;
  purchase_folio: string | null;
  remission_folio: string | null;
  product_id: string;
  product_name_snapshot: string | null;
  lot_code: string | null;
  customer_id: string | null;
  customer_name_snapshot: string | null;
  supplier_id: string | null;
  supplier_name_snapshot: string | null;
  delivery_address: string | null;
  movement_date: string;
  quantity_in: number;
  quantity_out: number;
  balance_after: number;
  unit_cost: number | null;
  unit_price: number | null;
  total_cost: number;
  total_sale: number;
  payment_status: string;
  paid_amount: number;
  balance_amount: number;
  notes: string | null;
  metadata?: Record<string, any> | null;
};

export function money(value: number | null | undefined) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(value || 0));
}

export function qty(value: number | null | undefined) {
  return new Intl.NumberFormat('es-MX', { maximumFractionDigits: 2 }).format(Number(value || 0));
}
