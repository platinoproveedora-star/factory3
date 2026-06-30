import type { SessionUser } from "./auth";

export type Gasto = {
  id?: string;
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
  current_balance: number;
  status: string;
};

function dataEnv() {
  const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos");
  return { url, key };
}

async function rpc<T>(fn: string, params: Record<string, any>): Promise<T> {
  const { url, key } = dataEnv();
  const res = await fetch(`${url}/rest/v1/rpc/${fn}`, {
    method: "POST",
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Prefer: "return=representation"
    },
    body: JSON.stringify(params),
    cache: "no-store"
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`supabase rpc ${fn} ${res.status}: ${text}`);
  return text ? (JSON.parse(text) as T) : ([] as T);
}

export async function listGastos(companyId: string, limit = 2000): Promise<Gasto[]> {
  const rows = await rpc<Record<string, any>[]>("g4all_list_gastos", {
    p_empresa_id: companyId,
    p_limit: limit
  });
  return rows.map(formatGastoRpc);
}

export async function listCategories(companyId: string) {
  return rpc<Array<{ id: string; nombre: string }>>("g4all_list_categorias", {
    p_empresa_id: companyId
  });
}

export async function listBankAccounts(companyId?: string) {
  const banksSchema = process.env.BANKS_SCHEMA;
  if (!banksSchema) return [];
  const { url, key } = dataEnv();
  const params: Record<string, string> = {
    select: "id,folio,account_name,bank_name,account_number_mask,current_balance,status",
    status: "eq.active",
    order: "account_name.asc",
    limit: "500"
  };
  if (companyId) params.empresa_id = `eq.${companyId}`;
  const qs = new URLSearchParams(params);
  try {
    const res = await fetch(`${url}/rest/v1/banks_accounts?${qs}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Accept-Profile": banksSchema,
        "Content-Type": "application/json"
      },
      cache: "no-store"
    });
    if (!res.ok) return [];
    const text = await res.text();
    return text ? (JSON.parse(text) as BankAccount[]) : [];
  } catch {
    return [];
  }
}

export function summarize(gastos: Gasto[]) {
  const total = gastos.reduce((sum, row) => sum + row.monto, 0);
  const byCategory = new Map<string, { total: number; count: number }>();
  for (const gasto of gastos) {
    const key = gasto.categoria || "Sin categoria";
    const current = byCategory.get(key) || { total: 0, count: 0 };
    current.total += gasto.monto;
    current.count += 1;
    byCategory.set(key, current);
  }
  return {
    total,
    count: gastos.length,
    avg: gastos.length ? total / gastos.length : 0,
    por_categoria: Array.from(byCategory.entries())
      .map(([categoria, values]) => ({ categoria, total: values.total, count: values.count }))
      .sort((a, b) => b.total - a.total)
  };
}

export async function createGasto(input: Record<string, any>, user: SessionUser, companyId: string) {
  const result = await rpc<Record<string, any>>("g4all_create_gasto", {
    p_row: {
      empresa_id: companyId,
      categoria: input.categoria || "",
      monto: Number(input.monto || 0),
      descripcion: String(input.descripcion || ""),
      fecha: String(input.fecha || new Date().toISOString().slice(0, 10)),
      vehiculo: input.vehiculo || null,
      cta_retiro_id: input.cta_retiro_id || null,
      cta_retiro_folio: input.cta_retiro_folio || null,
      cta_retiro_nombre: input.cta_retiro_nombre || null
    }
  });
  return { folio: result.folio, fecha: input.fecha, monto: Number(input.monto), descripcion: input.descripcion, metodo_captura: "dashboard", categoria: input.categoria || "", nombre_usuario: "apps4all", vehiculo: input.vehiculo || null } as Gasto;
}

export async function updateGasto(input: Record<string, any>, user: SessionUser, companyId: string) {
  const folio = String(input.folio || "");
  if (!folio) throw new Error("folio requerido");
  await rpc("g4all_update_gasto", {
    p_folio: folio,
    p_empresa_id: companyId,
    p_data: {
      monto: Number(input.monto || 0),
      fecha: input.fecha,
      descripcion: input.descripcion || "",
      vehiculo: input.vehiculo || null,
      categoria: input.categoria || null,
      cta_retiro_id: input.cta_retiro_id || null,
      cta_retiro_folio: input.cta_retiro_folio || null,
      cta_retiro_nombre: input.cta_retiro_nombre || null
    }
  });
  return { folio };
}

export async function deleteGasto(folio: string, user: SessionUser, companyId: string) {
  if (!folio) throw new Error("folio requerido");
  await rpc("g4all_delete_gasto", { p_folio: folio, p_empresa_id: companyId });
  return { deleted: true };
}

function formatGastoRpc(row: Record<string, any>): Gasto {
  return {
    id: row.id,
    folio: row.folio || "",
    fecha: row.fecha || "",
    monto: Number(row.monto || 0),
    descripcion: row.descripcion || "",
    metodo_captura: row.metodo_captura || "manual",
    vehiculo: row.vehiculo || null,
    cta_retiro_id: row.cta_retiro_id || null,
    cta_retiro_folio: row.cta_retiro_folio || null,
    cta_retiro_nombre: row.cta_retiro_nombre || null,
    categoria: row.categoria_nombre || "",
    nombre_usuario: row.usuario_nombre || ""
  };
}
