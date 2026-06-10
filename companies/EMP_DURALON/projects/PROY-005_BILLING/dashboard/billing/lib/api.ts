import projectContext from '../project-context.json';

const BASE = (process.env.NEXT_PUBLIC_FACTORY_API_URL ?? projectContext.factory_api_url ?? '').replace(/\/$/, '');
const WRITE_KEY = process.env.NEXT_PUBLIC_WRITE_KEY ?? '';

const ERP_CONTEXT = {
  company_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  empresa_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  project_code: process.env.NEXT_PUBLIC_ERP_BILLING_PROJECT_CODE ?? projectContext.project_code,
  module_code: process.env.NEXT_PUBLIC_ERP_BILLING_MODULE_CODE ?? projectContext.module_code,
  schema: process.env.NEXT_PUBLIC_ERP_BILLING_SCHEMA ?? projectContext.schema,
  billing_schema: process.env.NEXT_PUBLIC_ERP_BILLING_SCHEMA ?? projectContext.schema,
  sales_schema: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  schema_ventas: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
};

export type MoneyAccount = {
  id: string;
  folio: string;
  account_type: string;
  account_name: string;
  bank_name?: string | null;
  account_number_mask?: string | null;
  holder_name?: string | null;
  currency: string;
  responsible_user?: string | null;
  status: string;
  opening_balance?: number;
  current_balance?: number;
};

export type CollectionFolio = {
  id: string;
  folio: string;
  sales_folio?: string | null;
  customer_name?: string | null;
  expected_amount: number;
  collected_amount: number;
  balance_amount: number;
  status: string;
  collector_name?: string | null;
  due_date?: string | null;
  created_at?: string;
};

export type Payment = {
  id: string;
  folio: string;
  collection_folio?: string | null;
  customer_name?: string | null;
  payment_method: string;
  amount: number;
  unapplied_amount: number;
  payment_date: string;
  status: string;
  validation_status?: string;
  ocr_status?: string;
  bank_name?: string | null;
  reference?: string | null;
};

export type Remision = {
  id: string;
  folio: string;
  external_folio?: string | null;
  customer_name_snapshot: string;
  status: string;
  document_date: string;
  total: number;
  balance_total?: number;
};

export type DashboardData = {
  kpis: {
    collected_today: number;
    unapplied_total: number;
    receivable_total: number;
    active_accounts: number;
    pending_folios: number;
    pending_validation: number;
  };
  payments: Payment[];
  collection_folios: CollectionFolio[];
  money_accounts: MoneyAccount[];
  work_queue: {
    pending_folios: CollectionFolio[];
    pending_validation: Payment[];
  };
};

async function request<T>(skill: string, body: Record<string, unknown>, method: 'GET' | 'POST' = 'POST'): Promise<T> {
  if (!BASE) throw new Error('NEXT_PUBLIC_FACTORY_API_URL requerido');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (WRITE_KEY) headers['x-write-key'] = WRITE_KEY;
  let res: Response;
  if (method === 'GET') {
    const qs = new URLSearchParams(toQuery({ ...ERP_CONTEXT, ...body })).toString();
    res = await fetch(`${BASE}/data/${skill}${qs ? `?${qs}` : ''}`, { cache: 'no-store' });
  } else {
    res = await fetch(`${BASE}/data/${skill}`, {
      method: 'POST',
      headers,
      cache: 'no-store',
      body: JSON.stringify({ ...ERP_CONTEXT, ...body }),
    });
  }
  const text = await res.text();
  let json: any = {};
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { error: text };
  }
  if (!res.ok || json?.ok === false) {
    throw new Error(json?.detail || json?.error || `Factory error ${res.status}`);
  }
  return (json?.data ?? json) as T;
}

function toQuery(values: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
      .map(([key, value]) => [key, String(value)])
  );
}

export async function getDashboardData(): Promise<DashboardData> {
  return request<DashboardData>('vertical_erp_billing/erp_billing_dashboard_data', { limit: 80 }, 'GET');
}

export async function getMoneyAccounts(): Promise<MoneyAccount[]> {
  const data = await request<{ accounts: MoneyAccount[] }>('vertical_erp_billing/erp_billing_money_account_list', { limit: 200 }, 'GET');
  return data.accounts ?? [];
}

export async function getRemisiones(limit = 50): Promise<Remision[]> {
  const data = await request<{ remisiones: Remision[] }>(
    'vertical_erp_ventas/erp_ventas_remision_list',
    {
      schema: ERP_CONTEXT.sales_schema,
      schema_ventas: ERP_CONTEXT.sales_schema,
      project_code: projectContext.sales_project_code,
      module_code: projectContext.sales_module_code,
      limit,
    },
    'GET'
  );
  return data.remisiones ?? [];
}

export async function createMoneyAccount(payload: Partial<MoneyAccount> & { account_name: string; account_type: string }) {
  return request<{ account: MoneyAccount }>('vertical_erp_billing/erp_billing_money_account_create', { ...payload, dry_run: false });
}

export async function createCollectionFolio(payload: {
  sales_document_id?: string;
  sales_folio?: string;
  customer_name?: string;
  expected_amount: number;
  collector_name?: string;
}) {
  return request<{ collection_folio: CollectionFolio }>('vertical_erp_billing/erp_billing_collection_folio_create', { ...payload, dry_run: false });
}

export async function getCollectionFolioHtml(folio: string): Promise<string> {
  const data = await request<{ html: string }>('vertical_erp_billing/erp_billing_collection_folio_pdf', { folio }, 'GET');
  return data.html;
}

export async function createPayment(payload: {
  collection_folio_id?: string;
  collection_folio?: string;
  customer_name?: string;
  payment_method: string;
  amount: number;
  destination_money_account_id?: string;
  bank_name?: string;
  sender_account?: string;
  receiver_account?: string;
  tracking_key?: string;
  reference?: string;
  notes?: string;
}) {
  return request<{ payment: Payment }>('vertical_erp_billing/erp_billing_payment_create', { ...payload, dry_run: false });
}

export async function applyPayment(payload: { payment_id?: string; payment_folio?: string; sales_document_id: string; amount_applied: number }) {
  return request('vertical_erp_billing/erp_billing_payment_apply', { ...payload, dry_run: false });
}

export async function openHtml(html: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
