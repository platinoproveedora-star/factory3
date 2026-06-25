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
  banks_schema: process.env.NEXT_PUBLIC_ERP_BANKS_SCHEMA ?? projectContext.banks_schema,
  banks_project_code: process.env.NEXT_PUBLIC_ERP_BANKS_PROJECT_CODE ?? projectContext.banks_project_code,
  banks_module_code: projectContext.banks_module_code,
};

// ─── Types ────────────────────────────────────────────────────────────────────

export type MoneyAccount = {
  id: string;
  folio: string;
  account_type: string;
  account_name: string;
  bank_name?: string | null;
  account_number_mask?: string | null;
  currency: string;
  responsible_user?: string | null;
  status: string;
  current_balance?: number;
};

export type Remision = {
  id: string;
  folio: string;
  customer_id?: string | null;
  customer_name_snapshot: string;
  status: string;
  document_date: string;
  total: number;
  paid_total?: number;
  balance_total?: number;
  dias_vencido?: number;
};

export type Payment = {
  id: string;
  folio: string;
  customer_id?: string | null;
  customer_name?: string | null;
  payment_method: string;
  amount: number;
  unapplied_amount?: number;
  payment_date: string;
  destination_money_account_id?: string | null;
  status: string;
  confirmation_status?: string | null;
  bank_reference?: string | null;
  tracking_key?: string | null;
  notes?: string | null;
  receipt_file_url?: string | null;
  receipt_file_path?: string | null;
  receipt_file_bucket?: string | null;
  dias_esperando?: number;
  created_at?: string;
};

export type PaymentApplication = {
  id: string;
  folio: string;
  payment_id: string;
  payment_folio?: string | null;
  sales_folio?: string | null;
  amount_applied: number;
  status: string;
  created_at?: string;
};

export type Anticipo = {
  id: string;
  folio: string;
  customer_id?: string | null;
  customer_name?: string | null;
  amount: number;
  unapplied_amount?: number;
  payment_method: string;
  status: string;
  payment_date?: string | null;
  created_at?: string;
};

export type Devolucion = {
  id: string;
  folio: string;
  customer_id?: string | null;
  customer_name?: string | null;
  sales_document_folio?: string | null;
  amount: number;
  reason?: string | null;
  status: string;
  resolution?: string | null;
  created_at?: string;
};

export type KardexEntry = {
  fecha: string;
  tipo: string;
  folio?: string;
  concepto: string;
  cargo: number;
  abono: number;
  saldo: number;
  status?: string;
};

export type ClientStatementData = {
  customer_name: string;
  kpis: {
    total_facturado: number;
    total_cobrado: number;
    saldo_pendiente: number;
    saldo_pedidos?: number;
    anticipos_disponibles: number;
    remisiones_vencidas: number;
    ultimo_pago?: string | null;
    dias_sin_pagar?: number | null;
    ultima_compra?: string | null;
    dias_sin_comprar?: number | null;
    ticket_promedio: number;
    pago_promedio_mes: number;
    frecuencia_compra_dias?: number | null;
  };
  remisiones: Remision[];
  pedidos?: Remision[];
  payments: Payment[];
  anticipos_disponibles: Anticipo[];
  kardex: KardexEntry[];
};

export type ClientRankingRow = {
  customer_key: string;
  customer_name: string;
  semaforo: 'verde' | 'amarillo' | 'rojo';
  ultimo_pago?: string | null;
  dias_sin_pagar?: number | null;
  ultima_compra?: string | null;
  dias_sin_comprar?: number | null;
  ticket_promedio: number;
  pago_promedio_mes: number;
  m_actual: number;
  m1: number;
  m2: number;
  m3: number;
  total_3m: number;
};

export type ClientRankingData = {
  clientes: ClientRankingRow[];
  total_clientes: number;
  meses: { m_actual: string; m1: string; m2: string; m3: string };
  totales: {
    m_actual: number;
    m1: number;
    m2: number;
    m3: number;
    total_3m: number;
    promedio_mensual: number;
    proyeccion: number;
    tendencia_pct: number;
  };
};

export type CashCut = {
  id: string;
  folio?: string;
  cut_date: string;
  status: string;
  responsible_user?: string | null;
  destination_account_id?: string | null;
  destination_account_name?: string | null;
  created_at?: string;
};

export type CashCutData = {
  cut_date: string;
  ventas_dia: Remision[];
  pagos_hoy: Payment[];
  cxc_anteriores: Remision[];
  por_confirmar: Payment[];
  cortes_abiertos: CashCut[];
  totales: {
    total_ventas_dia: number;
    total_cobrado_dia: number;
    cxc_dia: number;
    total_pagos_hoy: number;
    total_cxc_anteriores: number;
    total_por_confirmar: number;
    por_cuenta: Record<string, number>;
  };
};

export type ConciliacionRow = {
  id: string;
  folio: string;
  account_folio?: string | null;
  amount: number;
  movement_date: string;
  source_folio?: string | null;
  clave_rastreo?: string | null;
  reconciliation_status?: string | null;
  notes?: string | null;
  payment?: Payment;
  match_type?: string;
};

export type ConciliacionData = {
  date_from: string;
  date_to: string;
  matched: ConciliacionRow[];
  solo_banco: ConciliacionRow[];
  solo_billing: Payment[];
  stats: {
    total_matched: number;
    total_solo_banco: number;
    total_solo_billing: number;
    importe_matched: number;
    importe_solo_banco: number;
    importe_solo_billing: number;
  };
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
  payment_applications: PaymentApplication[];
  money_accounts: MoneyAccount[];
};

// ─── Core request helper ──────────────────────────────────────────────────────

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
  try { json = text ? JSON.parse(text) : {}; } catch { json = { error: text }; }
  if (!res.ok || json?.ok === false) throw new Error(json?.detail || json?.error || `Factory error ${res.status}`);
  return (json?.data ?? json) as T;
}

function toQuery(values: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '')
      .map(([k, v]) => [k, String(v)])
  );
}

// ─── Remisiones ──────────────────────────────────────────────────────────────

export async function getRemisiones(filters?: {
  customer_name?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}): Promise<Remision[]> {
  const data = await request<{ remisiones: Remision[] }>(
    'vertical_erp_ventas/erp_ventas_remision_list',
    {
      schema: ERP_CONTEXT.sales_schema,
      schema_ventas: ERP_CONTEXT.sales_schema,
      project_code: projectContext.sales_project_code,
      module_code: projectContext.sales_module_code,
      ...(filters ?? {}),
      limit: filters?.limit ?? 100,
    },
    'GET'
  );
  return data.remisiones ?? [];
}

export async function getRemisionHtml(folio: string): Promise<string> {
  const data = await request<{ html: string }>(
    'vertical_erp_ventas/erp_ventas_remision_pdf',
    {
      folio,
      schema: ERP_CONTEXT.sales_schema,
      schema_ventas: ERP_CONTEXT.sales_schema,
      project_code: projectContext.sales_project_code,
      module_code: projectContext.sales_module_code,
    },
    'GET'
  );
  return data.html;
}

// ─── Pagos ────────────────────────────────────────────────────────────────────

export async function getDashboardData(limit = 100): Promise<DashboardData> {
  return request<DashboardData>(
    'vertical_erp_billing/erp_billing_dashboard_data',
    { limit },
    'GET'
  );
}

export async function createPayment(payload: {
  customer_name?: string;
  customer_id?: string;
  sales_document_id?: string;
  sales_folio?: string;
  payment_method: string;
  amount: number;
  destination_money_account_id?: string;
  bank_name?: string;
  tracking_key?: string;
  reference?: string;
  notes?: string;
}) {
  return request<{ payment: Payment }>('vertical_erp_billing/erp_billing_payment_create', {
    ...payload,
    banks_schema: ERP_CONTEXT.banks_schema,
    banks_project_code: ERP_CONTEXT.banks_project_code,
    dry_run: false,
  });
}

export async function applyPayment(payload: {
  payment_id?: string;
  payment_folio?: string;
  sales_document_id: string;
  amount_applied: number;
}) {
  return request('vertical_erp_billing/erp_billing_payment_apply', { ...payload, dry_run: false });
}

export async function confirmPayment(payload: {
  payment_id?: string;
  payment_folio?: string;
  bank_reference?: string;
}) {
  return request('vertical_erp_billing/erp_billing_payment_confirm', { ...payload, dry_run: false });
}

// ─── Anticipos ───────────────────────────────────────────────────────────────

export async function getAnticipos(filters?: {
  customer_name?: string;
  customer_id?: string;
  status?: string;
  limit?: number;
}): Promise<Anticipo[]> {
  const data = await request<{ anticipos: Anticipo[] }>(
    'vertical_erp_billing/erp_billing_anticipo_list',
    { ...(filters ?? {}), limit: filters?.limit ?? 100 },
    'GET'
  );
  return data.anticipos ?? [];
}

export async function createAnticipo(payload: {
  customer_name?: string;
  customer_id?: string;
  amount: number;
  payment_method: string;
  destination_money_account_id?: string;
  notes?: string;
}) {
  return request<{ anticipo: Anticipo }>('vertical_erp_billing/erp_billing_anticipo_create', {
    ...payload,
    banks_schema: ERP_CONTEXT.banks_schema,
    banks_project_code: ERP_CONTEXT.banks_project_code,
    dry_run: false,
  });
}

export async function applyAnticipo(payload: {
  anticipo_id?: string;
  anticipo_folio?: string;
  sales_document_id: string;
  amount_applied: number;
}) {
  return request('vertical_erp_billing/erp_billing_anticipo_apply', { ...payload, dry_run: false });
}

// ─── Devoluciones ─────────────────────────────────────────────────────────────

export async function getDevoluciones(filters?: {
  customer_name?: string;
  status?: string;
  limit?: number;
}): Promise<Devolucion[]> {
  const data = await request<{ devoluciones: Devolucion[] }>(
    'vertical_erp_billing/erp_billing_devolucion_list',
    { ...(filters ?? {}), limit: filters?.limit ?? 100 },
    'GET'
  );
  return data.devoluciones ?? [];
}

export async function createDevolucion(payload: {
  customer_name?: string;
  customer_id?: string;
  sales_document_folio?: string;
  amount: number;
  reason?: string;
}) {
  return request<{ devolucion: Devolucion }>('vertical_erp_billing/erp_billing_devolucion_create', {
    ...payload,
    dry_run: false,
  });
}

export async function applyDevolucion(payload: {
  devolucion_id?: string;
  devolucion_folio?: string;
  resolution: 'anticipo' | 'abono_remision';
  sales_document_id?: string;
}) {
  return request('vertical_erp_billing/erp_billing_devolucion_apply', { ...payload, dry_run: false });
}

// ─── Estado de Cuenta ─────────────────────────────────────────────────────────

export async function getClientStatement(
  customer_name: string,
  filters?: { date_from?: string; date_to?: string }
): Promise<ClientStatementData> {
  return request<ClientStatementData>(
    'vertical_erp_billing/erp_billing_client_statement',
    { customer_name, ...(filters ?? {}) },
    'GET'
  );
}

// ─── Ranking de clientes ──────────────────────────────────────────────────────

export async function getClientRanking(): Promise<ClientRankingData> {
  return request<ClientRankingData>('vertical_erp_billing/erp_billing_client_ranking', {}, 'GET');
}

// ─── Corte de Caja ────────────────────────────────────────────────────────────

export async function getCashCutData(cut_date?: string): Promise<CashCutData> {
  return request<CashCutData>(
    'vertical_erp_billing/erp_billing_cash_cut_data',
    cut_date ? { cut_date } : {},
    'GET'
  );
}

export async function openCashCut(payload: { responsible_user?: string; notes?: string }) {
  return request<{ cash_cut: CashCut }>('vertical_erp_billing/erp_billing_cash_cut_open', {
    ...payload,
    dry_run: false,
  });
}

export async function closeCashCut(payload: {
  cash_cut_id?: string;
  folio?: string;
  destination_account_id?: string;
  counted_amount?: number;
}) {
  return request<{ cash_cut: CashCut }>('vertical_erp_billing/erp_billing_cash_cut_close', {
    ...payload,
    dry_run: false,
  });
}

// ─── Cuentas de dinero ────────────────────────────────────────────────────────

export async function getMoneyAccounts(): Promise<MoneyAccount[]> {
  const data = await request<{ accounts: MoneyAccount[] }>(
    'vertical_erp_banks/erp_banks_account_list',
    {
      schema: ERP_CONTEXT.banks_schema,
      banks_schema: ERP_CONTEXT.banks_schema,
      project_code: ERP_CONTEXT.banks_project_code,
      module_code: ERP_CONTEXT.banks_module_code,
      limit: 200,
    },
    'GET'
  );
  return data.accounts ?? [];
}

// ─── Conciliación ─────────────────────────────────────────────────────────────

export async function getConciliacionData(filters: {
  date_from?: string;
  date_to?: string;
  account_id?: string;
}): Promise<ConciliacionData> {
  return request<ConciliacionData>(
    'vertical_erp_billing/erp_billing_conciliacion_data',
    { ...filters, banks_schema: ERP_CONTEXT.banks_schema },
    'GET'
  );
}

export async function ensureConciliacionTable() {
  return request('vertical_erp_billing/erp_billing_conciliacion_match', {
    action: 'ensure_table',
    dry_run: false,
  });
}

export async function createConciliacionMatch(payload: {
  movement_id: string;
  movement_folio?: string;
  payment_id?: string;
  payment_folio?: string;
  amount_matched?: number;
  notes?: string;
}) {
  return request('vertical_erp_billing/erp_billing_conciliacion_match', {
    ...payload,
    action: 'create',
    dry_run: false,
  });
}

export async function cancelConciliacionMatch(payload: { match_id?: string; folio?: string }) {
  return request('vertical_erp_billing/erp_billing_conciliacion_match', {
    ...payload,
    action: 'cancel',
    dry_run: false,
  });
}

// ─── Utils ────────────────────────────────────────────────────────────────────

export async function getReceiptLink(payload: {
  receipt_file_bucket: string;
  receipt_file_path: string;
}): Promise<{ url: string }> {
  return request<{ url: string }>('vertical_erp_billing/erp_billing_receipt_link_create', {
    ...payload,
    expires_in: 600,
    dry_run: false,
  });
}

export function openHtml(html: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
