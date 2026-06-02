const BASE = (process.env.NEXT_PUBLIC_FACTORY_API_URL ?? '').replace(/\/$/, '');
const WRITE_KEY = process.env.NEXT_PUBLIC_WRITE_KEY ?? '';

export type Customer = { id: string; folio: string; party_name: string; phone?: string; email?: string; address?: string };
export type Product  = { id: string; folio: string; product_name: string; sku?: string; unit: string; unit_price?: number; category?: string };
export type Remision = { id: string; folio: string; external_folio?: string; customer_name_snapshot: string; status: string; document_date: string; delivery_address?: string; total: number; created_at: string };

export type FormItem = {
  _key:        string;
  product_id:  string | null;
  description: string;
  quantity:    number;
  unit:        string;
  unit_price:  number;
  tax_rate:    number;
  tax_amount:  number;
  line_total:  number;
};

async function get<T>(skill: string, params: Record<string, string> = {}): Promise<T> {
  const qs  = new URLSearchParams(params).toString();
  const url = `${BASE}/data/${skill}${qs ? `?${qs}` : ''}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

async function post<T>(skill: string, body: object): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (WRITE_KEY) headers['x-write-key'] = WRITE_KEY;
  const res = await fetch(`${BASE}/data/${skill}`, { method: 'POST', headers, body: JSON.stringify(body) });
  if (!res.ok) {
    const txt = await res.text();
    let msg = txt;
    try { msg = JSON.parse(txt)?.detail ?? txt; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function getCustomers(): Promise<Customer[]> {
  const data = await get<{ customers: Customer[] }>('vertical_erp_ventas/erp_ventas_customer_list');
  return data.customers ?? [];
}

export async function getProducts(): Promise<Product[]> {
  const data = await get<{ products: Product[] }>('vertical_erp_ventas/erp_ventas_product_list');
  return data.products ?? [];
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
  items:           { product_id: string | null; description: string; quantity: number; unit: string; unit_price: number; tax_rate: number }[];
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
