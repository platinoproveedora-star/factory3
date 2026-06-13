import projectContext from '../project-context.json';

const BASE = (process.env.NEXT_PUBLIC_FACTORY_API_URL ?? projectContext.factory_api_url ?? '').replace(/\/$/, '');
const WRITE_KEY = process.env.NEXT_PUBLIC_WRITE_KEY ?? '';

const ERP_CONTEXT = {
  company_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  empresa_id: process.env.NEXT_PUBLIC_ERP_COMPANY_ID ?? projectContext.company_id,
  project_code: process.env.NEXT_PUBLIC_ERP_BILLING_PROJECT_CODE ?? projectContext.project_code,
  module_code: process.env.NEXT_PUBLIC_ERP_BILLING_MODULE_CODE ?? projectContext.module_code,
  schema: process.env.NEXT_PUBLIC_ERP_BILLING_SCHEMA ?? projectContext.schema,
  billing_schema: process.env.NEXT_PUBLIC_ERP_BILLING_SCHEMA ?? projectContext.billing_schema,
  sales_schema: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  schema_ventas: process.env.NEXT_PUBLIC_ERP_SALES_SCHEMA ?? projectContext.sales_schema,
  inventory_schema: process.env.NEXT_PUBLIC_ERP_INVENTORY_SCHEMA ?? projectContext.inventory_schema,
  schema_inventario: process.env.NEXT_PUBLIC_ERP_INVENTORY_SCHEMA ?? projectContext.inventory_schema,
  banks_schema: process.env.NEXT_PUBLIC_ERP_BANKS_SCHEMA ?? projectContext.banks_schema,
  banks_project_code: process.env.NEXT_PUBLIC_ERP_BANKS_PROJECT_CODE ?? projectContext.banks_project_code,
  banks_module_code: process.env.NEXT_PUBLIC_ERP_BANKS_MODULE_CODE ?? projectContext.banks_module_code,
  receipt_file_bucket: process.env.NEXT_PUBLIC_BILLING_RECEIPTS_BUCKET ?? projectContext.receipt_file_bucket,
};

export type Customer = {
  id: string;
  folio?: string;
  party_name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
};

export type MoneyAccount = {
  id: string;
  folio: string;
  account_type: string;
  account_name: string;
  bank_name?: string | null;
  account_number_mask?: string | null;
  current_balance?: number;
  status: string;
};

export type Remision = {
  id: string;
  folio: string;
  external_folio?: string | null;
  customer_id?: string | null;
  customer_name_snapshot: string;
  status: string;
  document_date: string;
  total: number;
  balance_total?: number;
};

export type CollectionFolio = {
  id: string;
  folio: string;
  customer_id?: string | null;
  customer_name?: string | null;
  expected_amount: number;
  balance_amount: number;
};

export type Payment = {
  id: string;
  folio: string;
  amount: number;
  unapplied_amount: number;
  status: string;
};

export type UploadPrepareResult = {
  bucket: string;
  path: string;
  signed_url: string;
  upload_method: 'PUT';
  content_type: string;
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

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export async function getCustomers(): Promise<Customer[]> {
  const data = await request<{ customers: Customer[] }>(
    'vertical_erp_ventas/erp_ventas_customer_list',
    { schema: ERP_CONTEXT.inventory_schema, inventory_schema: ERP_CONTEXT.inventory_schema, schema_inventario: ERP_CONTEXT.inventory_schema },
    'GET'
  );
  return data.customers ?? [];
}

export async function getAccounts(): Promise<MoneyAccount[]> {
  const data = await request<{ accounts: MoneyAccount[] }>(
    'vertical_erp_banks/erp_banks_account_list',
    {
      schema: ERP_CONTEXT.banks_schema,
      banks_schema: ERP_CONTEXT.banks_schema,
      project_code: ERP_CONTEXT.banks_project_code,
      module_code: ERP_CONTEXT.banks_module_code,
      status: 'active',
      limit: 200,
    },
    'GET'
  );
  return data.accounts ?? [];
}

export async function getRemisiones(customerId: string, limit = 200): Promise<Remision[]> {
  const data = await request<{ remisiones: Remision[] }>(
    'vertical_erp_ventas/erp_ventas_remision_list',
    {
      schema: ERP_CONTEXT.sales_schema,
      sales_schema: ERP_CONTEXT.sales_schema,
      schema_ventas: ERP_CONTEXT.sales_schema,
      customer_id: customerId,
      limit,
    },
    'GET'
  );
  return (data.remisiones ?? []).filter((row) => String(row.status || '').toLowerCase() !== 'cancelada' && Number(row.balance_total ?? row.total ?? 0) > 0);
}

export async function prepareReceiptUpload(file: File): Promise<UploadPrepareResult> {
  return request<UploadPrepareResult>('vertical_erp_billing/erp_billing_receipt_upload_prepare', {
    filename: file.name,
    content_type: file.type,
    size_bytes: file.size,
    receipt_file_bucket: ERP_CONTEXT.receipt_file_bucket,
    dry_run: false,
  });
}

export async function uploadReceipt(file: File, prepared: UploadPrepareResult) {
  const res = await fetch(prepared.signed_url, {
    method: prepared.upload_method || 'PUT',
    headers: { 'Content-Type': file.type || prepared.content_type || 'application/octet-stream' },
    body: file,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload comprobante ${res.status}: ${text}`);
  }
}

export async function createCollectionFolio(payload: {
  customer_id: string;
  customer_name: string;
  documents: Array<{
    sales_document_id: string;
    sales_folio: string;
    customer_id?: string | null;
    customer_name?: string | null;
    document_total: number;
    balance_total: number;
    amount_to_collect: number;
  }>;
  expected_amount: number;
}) {
  return request<{ collection_folio: CollectionFolio }>('vertical_erp_billing/erp_billing_collection_folio_create', {
    ...payload,
    dry_run: false,
  });
}

export async function createPayment(payload: {
  collection_folio_id?: string;
  collection_folio?: string;
  customer_id: string;
  customer_name: string;
  payment_method: string;
  amount: number;
  destination_money_account_id: string;
  bank_name?: string;
  reference?: string;
  tracking_key?: string;
  payment_date?: string;
  notes?: string;
  receipt_file_bucket?: string;
  receipt_file_path?: string;
  ocr_status?: string;
  validation_status?: string;
  metadata?: Record<string, unknown>;
}) {
  return request<{ payment: Payment }>('vertical_erp_billing/erp_billing_payment_create', {
    ...payload,
    banks_schema: ERP_CONTEXT.banks_schema,
    banks_project_code: ERP_CONTEXT.banks_project_code,
    dry_run: false,
  });
}

export async function applyPayment(payload: { payment_id: string; sales_document_id: string; amount_applied: number }) {
  return request('vertical_erp_billing/erp_billing_payment_apply', { ...payload, dry_run: false });
}
