/**
 * Cliente del dashboard Duralon (EMP_DURALON / PROY-001 / gastos).
 * Llama a factory3 /data/vertical_client_expenses/client_expenses_dashboard_data.
 * Cero credenciales Supabase expuestas; factory3 maneja service_role_key internamente.
 */

const FACTORY_URL = (
  process.env.FACTORY_API_URL ?? process.env.NEXT_PUBLIC_FACTORY_API_URL ?? ''
).replace(/\/$/, '');
const DASHBOARD_KEY = process.env.DASHBOARD_KEY ?? '';

async function factoryGet<T>(skill: string, params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const url = `${FACTORY_URL}/data/${skill}${qs ? `?${qs}` : ''}`;
  const headers: Record<string, string> = DASHBOARD_KEY ? { 'X-Dashboard-Key': DASHBOARD_KEY } : {};
  const res = await fetch(url, { cache: 'no-store', headers });
  if (!res.ok) throw new Error(`factory3 ${res.status}: ${await res.text()}`);
  const json = await res.json();
  if (json?.ok === false) throw new Error(json.error ?? 'factory3 error');
  if (json?.ok === true && 'data' in json) return json.data as T;
  return json as T;
}

export type Gasto = {
  folio: string;
  fecha: string;
  monto: number;
  descripcion: string;
  metodo_captura: string;
  categoria: string;
  nombre_usuario: string;
};

export type StatCategoria = { categoria: string; total: number; count: number };

export type Stats = {
  total: number;
  count: number;
  avg: number;
  por_categoria: StatCategoria[];
  totalMes: number;
  totalMesAnt: number;
  variacion: number;
};

function baseParams(extra: Record<string, string> = {}) {
  return {
    company_id: 'EMP_DURALON',
    project_code: 'PROY-001',
    module_code: 'gastos',
    ...extra,
  };
}

export async function getGastos(limit = 200): Promise<Gasto[]> {
  const data = await factoryGet<{ gastos: Gasto[]; total: number }>(
    'vertical_client_expenses/client_expenses_dashboard_data',
    baseParams({ action: 'list', limit: String(limit) })
  );
  return data.gastos ?? [];
}

export async function getStats(): Promise<Stats> {
  return factoryGet<Stats>(
    'vertical_client_expenses/client_expenses_dashboard_data',
    baseParams({ action: 'stats' })
  );
}
