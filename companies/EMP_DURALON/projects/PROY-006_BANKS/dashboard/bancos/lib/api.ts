export type Account = {
  id: string;
  folio: string;
  account_type: string;
  account_name: string;
  bank_name: string | null;
  account_number: string | null;
  account_number_mask: string | null;
  holder_name: string | null;
  currency: string;
  responsible_user: string | null;
  current_balance: number;
  opening_balance: number;
  status: string;
  metadata: Record<string, any> | null;
};

export type Movement = {
  id: string;
  folio: string;
  account_id: string;
  account_folio: string;
  movement_type: 'entrada' | 'salida';
  source_type: string;
  source_module: string | null;
  source_id: string | null;
  source_folio: string | null;
  amount: number;
  balance_before: number | null;
  balance_after: number | null;
  movement_date: string;
  authorization_status: string;
  authorization_id: string | null;
  reconciliation_status: string;
  notes: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
};

export type Authorization = {
  id: string;
  folio: string;
  movement_id: string;
  status: string;
  requested_at: string;
  decided_at: string | null;
  decision_notes: string | null;
};

export type DashboardData = {
  accounts: Account[];
  movements: Movement[];
  authorizations: Authorization[];
  kpis: {
    total_balance: number;
    active_accounts: number;
    pending_authorizations: number;
    pending_reconciliation: number;
    month_in: number;
    month_out: number;
  };
};

export type StatementExtraction = {
  id: string;
  folio: string;
  empresa_id: string;
  bank_profile: string;
  bank_name: string | null;
  holder_name: string | null;
  clabe: string | null;
  account_number_mask: string | null;
  statement_period_start: string | null;
  statement_period_end: string | null;
  file_name: string | null;
  file_hash: string;
  total_lines_extracted: number;
  total_deposits_reported: number | null;
  total_deposits_extracted: number | null;
  validation_diff_deposits: number | null;
  total_withdrawals_reported: number | null;
  total_withdrawals_extracted: number | null;
  validation_diff_withdrawals: number | null;
  validation_status: string;
  status: string;
  warnings: string[];
  created_at: string;
};

export type StatementLine = {
  id: string;
  folio: string;
  raw_line_order: number;
  line_date: string;
  description: string | null;
  direction: 'deposito' | 'retiro';
  amount: number;
  saldo: number | null;
  clave_rastreo: string | null;
  referencia: string | null;
  nombre_origen: string | null;
  cuenta_origen: string | null;
  nombre_destino: string | null;
  cuenta_destino: string | null;
  confidence: number;
  parse_warnings: string[];
  raw_text: string;
  metadata: Record<string, any> | null;
};

export type ExpenseReconciliationRow = {
  id: string;
  folio: string;
  fecha: string;
  monto: number;
  descripcion: string | null;
  vehiculo: string | null;
  usuario_id: string | null;
  categoria_id: string | null;
  estado: string | null;
  cta_retiro_id?: string | null;
  cta_retiro_folio?: string | null;
  cta_retiro_nombre?: string | null;
  linked: boolean;
  bank_movement: Movement | null;
};

export type ExpenseReconciliationData = {
  expenses: ExpenseReconciliationRow[];
  default_source_account: {
    id: string;
    folio: string;
    account_name: string;
    current_balance: number;
    status: string;
  } | null;
  expense_counterparty_name: string;
  summary: {
    total: number;
    pending: number;
    linked: number;
  };
};

export type ApiResponse<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

const keyStorage = 'uc101_bancos_dashboard_key';

export function money(value: number | null | undefined) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(value || 0));
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function getStoredKey() {
  if (typeof window === 'undefined') return '';
  return window.sessionStorage.getItem(keyStorage) || '';
}

export function storeKey(key: string) {
  if (typeof window === 'undefined') return;
  window.sessionStorage.setItem(keyStorage, key);
}

export function clearKey() {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(keyStorage);
}

export async function login(key: string) {
  const response = await fetch('/api/auth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key })
  });
  const result = (await response.json()) as ApiResponse<{ authenticated: boolean }>;
  if (!result.ok) throw new Error(result.error || 'Clave invalida');
  storeKey(key);
  return true;
}

export async function banksApi<T>(action: string, payload: Record<string, any> = {}) {
  const response = await fetch('/api/banks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-dashboard-key': getStoredKey()
    },
    body: JSON.stringify({ action, payload })
  });
  const result = (await response.json()) as ApiResponse<T>;
  if (!result.ok) throw new Error(result.error || 'Error en bancos');
  return result.data as T;
}
