import projectContext from '../project-context.json';

const BASE = (process.env.NEXT_PUBLIC_FACTORY_API_URL ?? '').replace(/\/$/, '');
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

export type Customer = { id: string; folio: string; party_name: string; phone?: string; email?: string; address?: string };
export type Product  = { id: string; folio: string; product_name: string; sku?: string; unit: string; unit_price?: number; category?: string };
export type Remision = { id: string; folio: string; external_folio?: string; customer_name_snapshot: string; status: string; document_date: string; delivery_address?: string; total: number; created_at: string };
export type ProductLot = { lot_code: string; quantity: number; lot_cost: number; avg_cost: number; last_cost: number; label: string };
export type ProductLotOptions = { lots: ProductLot[]; requires_lot: boolean; default_lot_code?: string | null; avg_cost: number; last_cost: number };

export type FormItem = {
  _key:        string;
  product_id:  string | null;
  lot_code:    string | null;
  lots:        ProductLot[];
  requires_lot: boolean;
  lots_loading: boolean;
  description: string;
  quantity:    number;
  unit:        string;
  unit_price:  number;
  tax_rate:    number;
  tax_amount:  number;
  line_total:  number;
};

async function get<T>(skill: string, params: Record<string, string> = {}): Promise<T> {
  const qs  = new URLSearchParams({ ...toQuery(ERP_CONTEXT), ...params }).toString();
  const url = `${BASE}/data/${skill}${qs ? `?${qs}` : ''}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

async function post<T>(skill: string, body: object): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (WRITE_KEY) headers['x-write-key'] = WRITE_KEY;
  const res = await fetch(`${BASE}/data/${skill}`, { method: 'POST', headers, body: JSON.stringify({ ...ERP_CONTEXT, ...body }) });
  if (!res.ok) {
    const txt = await res.text();
    let msg = txt;
    try { msg = JSON.parse(txt)?.detail ?? txt; } catch {}
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

export async function getCustomers(): Promise<Customer[]> {
  const data = await get<{ customers: Customer[] }>('vertical_erp_ventas/erp_ventas_customer_list');
  return data.customers ?? [];
}

export async function getProducts(): Promise<Product[]> {
  const data = await get<{ products: Product[] }>('vertical_erp_ventas/erp_ventas_product_list');
  return data.products ?? [];
}

export async function getProductLots(productId: string): Promise<ProductLotOptions> {
  const data = await get<ProductLotOptions>('vertical_erp_inventory/erp_inventory_lot_options', { product_id: productId });
  return { lots: data.lots ?? [], requires_lot: Boolean(data.requires_lot), default_lot_code: data.default_lot_code ?? null, avg_cost: data.avg_cost ?? 0, last_cost: data.last_cost ?? 0 };
}

export async function getRemisiones(limit = 20): Promise<Remision[]> {
  const data = await get<{ remisiones: Remision[] }>('vertical_erp_ventas/erp_ventas_remision_list', { limit: String(limit) });
  return data.remisiones ?? [];
}

export async function createRemision(payload: {
  customer_id?:   string;
  customer_name?: string;
  document_date:  string;
  delivery_address?: string;
  external_folio?: string;
  notes?:          string;
  items:           { product_id: string | null; lot_code?: string | null; description: string; quantity: number; unit: string; unit_price: number; tax_rate: number }[];
}): Promise<{ folio: string; total: number; items: string[] }> {
  return post('vertical_erp_ventas/erp_ventas_remision_create', { ...payload, dry_run: false });
}

export async function getRemisionPdfHtml(folio: string): Promise<string> {
  const data = await get<{ html: string }>('vertical_erp_ventas/erp_ventas_remision_pdf', { folio });
  return data.html;
}

export async function openRemisionPdf(folio: string) {
  const html = await getRemisionPdfHtml(folio);
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
