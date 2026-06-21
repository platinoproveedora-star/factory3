import { NextResponse } from 'next/server';
import projectContext from '../../../project-context.json';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const fetchCache = 'force-no-store';

type SupabaseOptions = {
  method?: 'GET' | 'POST' | 'PATCH';
  query?: Record<string, string>;
  body?: Record<string, any>;
};

const noStoreHeaders = { 'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate' };

function env(name: string) {
  return String(process.env[name] || '').trim();
}

function requireDashboardKey(request: Request) {
  const configured = env('DASHBOARD_KEY');
  const received = String(request.headers.get('x-dashboard-key') || '').trim();
  if (!configured) return 'DASHBOARD_KEY no configurada';
  if (!received || received !== configured) return 'Clave invalida';
  return '';
}

function schema() {
  return env('SUPABASE_SCHEMA') || projectContext.schema;
}

function companyId() {
  return env('COMPANY_ID') || projectContext.company_id;
}

function projectCode() {
  return env('PROJECT_CODE') || projectContext.project_code;
}

function moduleCode() {
  return env('MODULE_CODE') || projectContext.module_code;
}

async function supabase(path: string, options: SupabaseOptions = {}) {
  const url = env('SUPABASE_URL');
  const key = env('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !key) throw new Error('Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY');

  const params = new URLSearchParams(options.query || {});
  const endpoint = `${url.replace(/\/$/, '')}/rest/v1/${path}${params.size ? `?${params}` : ''}`;
  const response = await fetch(endpoint, {
    method: options.method || 'GET',
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      Prefer: 'return=representation',
      'Accept-Profile': schema(),
      'Content-Profile': schema()
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: 'no-store'
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = data?.message || data?.error || `Supabase ${response.status}`;
    throw new Error(message);
  }
  return data;
}

async function rpc<T>(name: string, body: Record<string, any>) {
  return (await supabase(`rpc/${name}`, { method: 'POST', body })) as T;
}

function numberValue(value: any) {
  return Number(value || 0);
}

function monthStart() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-01`;
}

async function loadDashboard() {
  const accountQuery = {
    select: 'id,folio,account_type,account_name,bank_name,account_number_mask,currency,current_balance,opening_balance,status',
    empresa_id: `eq.${companyId()}`,
    order: 'account_name.asc'
  };
  const movementQuery = {
    select: 'id,folio,account_id,account_folio,movement_type,source_type,source_module,source_id,source_folio,amount,balance_before,balance_after,movement_date,authorization_status,authorization_id,reconciliation_status,notes,created_at',
    empresa_id: `eq.${companyId()}`,
    order: 'movement_date.desc,created_at.desc',
    limit: '80'
  };
  const authQuery = {
    select: 'id,folio,movement_id,status,requested_at,decided_at,decision_notes',
    empresa_id: `eq.${companyId()}`,
    order: 'requested_at.desc',
    limit: '80'
  };

  const [accounts, movements, authorizations] = await Promise.all([
    supabase('banks_accounts', { query: accountQuery }),
    supabase('banks_movements', { query: movementQuery }),
    supabase('banks_authorizations', { query: authQuery })
  ]);

  const start = monthStart();
  const kpis = {
    total_balance: accounts.reduce((sum: number, row: any) => sum + numberValue(row.current_balance), 0),
    active_accounts: accounts.filter((row: any) => row.status === 'active').length,
    pending_authorizations: authorizations.filter((row: any) => row.status === 'pendiente').length,
    pending_reconciliation: movements.filter((row: any) => row.reconciliation_status === 'pendiente').length,
    month_in: movements
      .filter((row: any) => row.movement_date >= start && row.movement_type === 'entrada' && row.authorization_status !== 'rechazado')
      .reduce((sum: number, row: any) => sum + numberValue(row.amount), 0),
    month_out: movements
      .filter((row: any) => row.movement_date >= start && row.movement_type === 'salida' && row.authorization_status !== 'rechazado')
      .reduce((sum: number, row: any) => sum + numberValue(row.amount), 0)
  };

  return { accounts, movements, authorizations, kpis };
}

async function createAccount(payload: Record<string, any>) {
  const folio = await rpc<string>('reserve_erp_folio', {
    p_scope: 'banks_accounts',
    p_prefix: 'BAC',
    p_digits: 5,
    p_empresa_id: companyId(),
    p_project_code: projectCode(),
    p_module_code: moduleCode()
  });

  const rows = await supabase('banks_accounts', {
    method: 'POST',
    body: {
      folio,
      empresa_id: companyId(),
      project_code: projectCode(),
      module_code: moduleCode(),
      account_type: payload.account_type || 'bank',
      account_name: payload.account_name,
      bank_name: payload.bank_name || null,
      account_number_mask: payload.account_number_mask || null,
      holder_name: payload.holder_name || null,
      currency: payload.currency || 'MXN',
      opening_balance: numberValue(payload.opening_balance),
      current_balance: numberValue(payload.opening_balance),
      status: 'active',
      metadata: {}
    }
  });
  return rows?.[0] || null;
}

async function recordMovement(payload: Record<string, any>) {
  const sourceId = payload.source_id || `dashboard-${crypto.randomUUID()}`;
  return rpc<any>('banks_record_movement', {
    p_account_id: payload.account_id || null,
    p_account_folio: payload.account_folio || null,
    p_movement_type: payload.movement_type,
    p_source_type: payload.source_type || 'ajuste',
    p_source_module: payload.source_module || 'dashboard',
    p_source_id: sourceId,
    p_source_folio: payload.source_folio || null,
    p_amount: numberValue(payload.amount),
    p_movement_date: payload.movement_date || new Date().toISOString().slice(0, 10),
    p_transfer_group_id: payload.transfer_group_id || null,
    p_reversal_of_movement_id: payload.reversal_of_movement_id || null,
    p_clave_rastreo: payload.clave_rastreo || null,
    p_value_date: payload.value_date || null,
    p_notes: payload.notes || null,
    p_metadata: payload.metadata || {},
    p_empresa_id: companyId(),
    p_project_code: projectCode(),
    p_module_code: moduleCode(),
    p_requested_by: payload.requested_by || null
  });
}

async function decideAuthorization(payload: Record<string, any>) {
  return rpc<any>('banks_decide_authorization', {
    p_authorization_id: payload.authorization_id,
    p_decision: payload.decision,
    p_decided_by: payload.decided_by || env('DEFAULT_AUTHORIZER_USER_ID') || null,
    p_decision_notes: payload.decision_notes || null,
    p_empresa_id: companyId()
  });
}

async function markReconciled(payload: Record<string, any>) {
  const rows = await supabase('banks_movements', {
    method: 'PATCH',
    query: {
      id: `eq.${payload.movement_id}`,
      empresa_id: `eq.${companyId()}`
    },
    body: {
      reconciliation_status: payload.reconciliation_status || 'conciliado',
      reconciled_at: new Date().toISOString()
    }
  });
  return rows?.[0] || null;
}

export async function POST(request: Request) {
  const authError = requireDashboardKey(request);
  if (authError) {
    return NextResponse.json({ ok: false, error: authError }, { status: authError.includes('configurada') ? 500 : 401, headers: noStoreHeaders });
  }

  try {
    const body = await request.json();
    const action = String(body.action || '');
    const payload = body.payload || {};
    const actions: Record<string, () => Promise<any>> = {
      dashboard: loadDashboard,
      create_account: () => createAccount(payload),
      record_movement: () => recordMovement(payload),
      decide_authorization: () => decideAuthorization(payload),
      mark_reconciled: () => markReconciled(payload)
    };

    if (!actions[action]) {
      return NextResponse.json({ ok: false, error: 'Accion no soportada' }, { status: 400, headers: noStoreHeaders });
    }

    const data = await actions[action]();
    return NextResponse.json({ ok: true, data }, { headers: noStoreHeaders });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || 'Error en bancos' }, { status: 500, headers: noStoreHeaders });
  }
}
