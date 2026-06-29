import { dataSkill } from "./factory";
import { SCHEMA } from "./auth";

export type Gasto = {
  folio: string;
  fecha: string;
  monto: number;
  descripcion: string;
  metodo_captura: string;
  categoria: string;
  nombre_usuario: string;
  vehiculo: string | null;
  cta_retiro_id?: string | null;
  cta_retiro_folio?: string | null;
  cta_retiro_nombre?: string | null;
};

export type BankAccount = {
  id: string;
  folio: string;
  account_name: string;
  bank_name: string | null;
  account_number_mask: string | null;
  status: string;
  current_balance: number;
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

function baseCtx(empresaId: string, extra: Record<string, unknown> = {}) {
  return {
    schema: SCHEMA,
    company_id: empresaId,
    empresa_id: empresaId,
    project_code: "GASTOS4ALL_V1",
    module_code: "gastos4all",
    ...extra,
  };
}

export async function getGastos(empresaId: string, limit = 2000): Promise<Gasto[]> {
  const data = await dataSkill<{ gastos: Gasto[] }>(
    "vertical_client_expenses/client_expenses_dashboard_data",
    baseCtx(empresaId, { action: "list", limit: String(limit) })
  );
  return data.gastos ?? [];
}

export async function getStats(empresaId: string): Promise<Stats> {
  return dataSkill<Stats>(
    "vertical_client_expenses/client_expenses_dashboard_data",
    baseCtx(empresaId, { action: "stats" })
  );
}
