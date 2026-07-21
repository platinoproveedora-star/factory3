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
  logistics_schema: process.env.NEXT_PUBLIC_ERP_LOGISTICS_SCHEMA ?? projectContext.logistics_schema,
  logistics_project_code: process.env.NEXT_PUBLIC_ERP_LOGISTICS_PROJECT_CODE ?? projectContext.logistics_project_code,
  logistics_module_code: process.env.NEXT_PUBLIC_ERP_LOGISTICS_MODULE_CODE ?? projectContext.logistics_module_code,
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
  quantity?: number | null;
  current_stock?: number | null;
  stock_status?: string | null;
  weight_kg?: number | null;
  weight_unit?: string | null;
};

export type PedidoStatus = 'pedido' | 'liberado' | 'remisionado' | 'cancelado' | string;

export type Pedido = {
  id: string;
  folio: string;
  external_folio?: string | null;
  customer_id: string;
  customer_name_snapshot: string;
  status: PedidoStatus;
  document_date: string;
  due_date?: string | null;
  delivery_address?: string | null;
  payment_method?: string | null;
  city?: string | null;
  city_quadrant?: string | null;
  total_weight_kg?: number | null;
  subtotal: number;
  tax_total: number;
  total: number;
  balance_total?: number | null;
  notes?: string | null;
  metadata?: Record<string, unknown> | null;
  items?: PedidoItem[];
};

export type PedidoItem = {
  id?: string;
  folio?: string;
  product_id: string | null;
  inventory_product_id?: string | null;
  description: string;
  quantity: number;
  unit: string;
  lot_code?: string | null;
  unit_price?: number | null;
  unit_price_ex_vat?: number | null;
  vat_rate?: number | null;
  tax_rate?: number | null;
  line_total?: number | null;
  weight_kg_per_unit?: number | null;
  weight_source?: 'catalog' | 'missing' | string | null;
};

export type FormItem = {
  _key: string;
  product_id: string | null;
  description: string;
  quantity: number;
  current_stock?: number | null;
  unit: string;
  lot_code: string | null;
  unit_price_ex_vat: number;
  vat_rate: number;
  weight_kg_per_unit: number;
  weight_source: 'catalog' | 'missing';
};

export type LotOption = {
  lot_code: string;
  quantity: number;
  lot_cost: number;
  avg_cost: number;
  last_movement_date?: string | null;
  label: string;
};

export type RemisionResult = {
  folio: string;
  document_id: string;
  total: number;
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

export function emptyItem(): FormItem {
  return {
    _key: crypto.randomUUID(),
    product_id: null,
    description: '',
    quantity: 1,
    unit: 'pieza',
    lot_code: null,
    unit_price_ex_vat: 0,
    vat_rate: 0.16,
    weight_kg_per_unit: 0,
    weight_source: 'missing',
  };
}

export function editableStatus(status?: string | null) {
  return status === 'pedido' || status === 'liberado' || !status;
}

export async function getCustomers(): Promise<Customer[]> {
  const data = await get<{ customers: Customer[] }>('vertical_erp_ventas/erp_ventas_customer_list');
  return data.customers ?? [];
}

export async function getProducts(): Promise<Product[]> {
  const data = await get<{ products: Product[] }>('vertical_erp_ventas/erp_ventas_product_list');
  return data.products ?? [];
}

export async function getLotOptions(productId: string): Promise<{ lots: LotOption[]; requires_lot: boolean; default_lot_code: string | null }> {
  return get('vertical_erp_inventory/erp_inventory_lot_options', { product_id: productId });
}

export async function getPedidos(limit = 50): Promise<Pedido[]> {
  const data = await get<{ pedidos: Pedido[] }>('vertical_erp_ventas/erp_ventas_pedido_list', { limit: String(limit), include_items: 'true' });
  return data.pedidos ?? [];
}

export async function getPedidoDetail(folio: string): Promise<{ pedido: Pedido; items: PedidoItem[] }> {
  return get('vertical_erp_ventas/erp_ventas_pedido_detail', { folio });
}

export async function createPedido(payload: PedidoPayload): Promise<{ pedido: Pedido }> {
  return post('vertical_erp_ventas/erp_ventas_pedido_create', { ...payload, dry_run: false });
}

export async function updatePedido(payload: PedidoPayload & { id: string }): Promise<{ pedido: Pedido }> {
  return post('vertical_erp_ventas/erp_ventas_pedido_update', { ...payload, dry_run: false });
}

export async function pedidoToRemision(payload: { pedido_id: string; document_date?: string; notes?: string }): Promise<{ pedido: Pedido; remision: RemisionResult }> {
  return post('vertical_erp_ventas/erp_ventas_pedido_to_remision', { ...payload, dry_run: false });
}

export async function cancelPedido(payload: { id: string; cancel_reason?: string }): Promise<{ pedido: Pedido }> {
  return post('vertical_erp_ventas/erp_ventas_pedido_cancel', { ...payload, dry_run: false });
}

export async function getPedidoPdfHtml(folio: string): Promise<string> {
  const data = await get<{ html: string }>('vertical_erp_ventas/erp_ventas_pedido_pdf', { folio });
  return data.html;
}

export async function getRemisionPdfHtml(folio: string): Promise<string> {
  const data = await get<{ html: string }>('vertical_erp_ventas/erp_ventas_remision_pdf', { folio });
  return data.html;
}

async function openHtml(html: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export async function openPedidoPdf(folio: string) {
  openHtml(await getPedidoPdfHtml(folio));
}

export async function openRemisionPdf(folio: string) {
  openHtml(await getRemisionPdfHtml(folio));
}

export type PedidoPayload = {
  customer_id?: string;
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
    lot_code?: string | null;
    unit_price_ex_vat: number;
    vat_rate: number;
  }>;
};
