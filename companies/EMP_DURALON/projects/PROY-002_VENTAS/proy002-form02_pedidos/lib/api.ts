import projectContext from '../project-context.json';

const BASE = (process.env.NEXT_PUBLIC_FACTORY_API_URL ?? projectContext.factory_api_url ?? '').replace(/\/$/, '');
const WRITE_KEY = process.env.NEXT_PUBLIC_WRITE_KEY ?? '';

const ERP_CONTEXT = {
  company_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  empresa_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  project_code: process.env.NEXT_PUBLIC_ERP_SALES_PROJECT_CODE ?? projectContext.sales_project_code,
  module_code: process.env.NEXT_PUBLIC_ERP_SALES_MODULE_CODE ?? projectContext.sales_module_code,
  schema: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  schema_ventas: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  sales_schema: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  schema_inventario: process.env.NEXT_PUBLIC_ERP_INVENTORY_SCHEMA ?? projectContext.inventory_schema,
  inventory_schema: process.env.NEXT_PUBLIC_ERP_INVENTORY_SCHEMA ?? projectContext.inventory_schema,
  project_inv: process.env.NEXT_PUBLIC_ERP_INVENTORY_PROJECT_CODE ?? projectContext.inventory_project_code,
  inventory_project_code: process.env.NEXT_PUBLIC_ERP_INVENTORY_PROJECT_CODE ?? projectContext.inventory_project_code,
  module_inv: process.env.NEXT_PUBLIC_ERP_INVENTORY_MODULE_CODE ?? projectContext.inventory_module_code,
  inventory_module_code: process.env.NEXT_PUBLIC_ERP_INVENTORY_MODULE_CODE ?? projectContext.inventory_module_code,
};

export type Customer = {
  id: string;
  folio: string;
  party_name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
};

export type Product = {
  id: string;
  folio: string;
  product_name: string;
  sku?: string | null;
  unit: string;
  category?: string | null;
  weight_kg?: number | null;
  weight_unit?: string | null;
  weight_notes?: string | null;
};

export type Pedido = {
  id: string;
  folio: string;
  customer_name_snapshot: string;
  total: number;
  total_weight_kg: number;
};

export type FormItem = {
  _key: string;
  product_id: string | null;
  description: string;
  quantity: number;
  unit: string;
  unit_price_ex_vat: number;
  vat_rate: number;
  weight_kg_per_unit: number;
  weight_source: 'catalog' | 'missing';
};

async function get<T>(skill: string, params: Record<string, string> = {}): Promise<T> {
  if (!BASE) throw new Error('NEXT_PUBLIC_FACTORY_API_URL requerido');
  const qs = new URLSearchParams({ ...toQuery(ERP_CONTEXT), ...params }).toString();
  const res = await fetch(`${BASE}/data/${skill}${qs ? `?${qs}` : ''}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

async function post<T>(skill: string, body: object): Promise<T> {
  if (!BASE) throw new Error('NEXT_PUBLIC_FACTORY_API_URL requerido');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (WRITE_KEY) headers['x-write-key'] = WRITE_KEY;
  const res = await fetch(`${BASE}/data/${skill}`, {
    method: 'POST',
    headers,
    cache: 'no-store',
    body: JSON.stringify({ ...ERP_CONTEXT, ...body }),
  });
  if (!res.ok) {
    const txt = await res.text();
    let msg = txt;
    try {
      msg = JSON.parse(txt)?.detail ?? txt;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function toQuery(values: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
      .map(([key, value]) => [key, String(value)])
  );
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export async function getCustomers(): Promise<Customer[]> {
  const data = await get<{ customers: Customer[] }>('vertical_erp_ventas/erp_ventas_customer_list');
  return data.customers ?? [];
}

export async function getProducts(): Promise<Product[]> {
  const data = await get<{ products: Product[] }>('vertical_erp_ventas/erp_ventas_product_list');
  return data.products ?? [];
}

export async function createPedido(payload: {
  customer_id: string;
  customer_name?: string;
  document_date: string;
  due_date?: string;
  delivery_address?: string;
  city?: string;
  city_quadrant?: string;
  payment_method: string;
  external_folio?: string;
  notes?: string;
  items: Array<{
    product_id: string | null;
    description: string;
    quantity: number;
    unit: string;
    unit_price_ex_vat: number;
    vat_rate: number;
  }>;
}): Promise<{ pedido: Pedido }> {
  return post('vertical_erp_ventas/erp_ventas_pedido_create', { ...payload, dry_run: false });
}

export async function getPedidoPdfHtml(folio: string): Promise<string> {
  const data = await get<{ html: string }>('vertical_erp_ventas/erp_ventas_pedido_pdf', { folio });
  return data.html;
}

export async function openPedidoPdf(folio: string) {
  const html = await getPedidoPdfHtml(folio);
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
