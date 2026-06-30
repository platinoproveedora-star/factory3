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

const SCHEMA = "gastos4all";

function dataEnv() {
  const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos");
  return { url, key };
}

async function rest<T>(schema: string, path: string, init: RequestInit = {}) {
  const { url, key } = dataEnv();
  const res = await fetch(`${url}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Accept-Profile": schema,
      "Content-Profile": schema,
      "Content-Type": "application/json",
      Prefer: "return=representation",
      ...(init.headers || {})
    },
    cache: "no-store"
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`supabase ${res.status}: ${text}`);
  return text ? (JSON.parse(text) as T) : ([] as T);
}

export async function listGastos(companyId: string, limit = 2000) {
  const select = [
    "id",
    "folio",
    "fecha",
    "monto",
    "descripcion",
    "metodo_captura",
    "vehiculo",
    "cta_retiro_id",
    "cta_retiro_folio",
    "cta_retiro_nombre",
    "categorias_gasto(nombre)",
    "usuarios(nombre)"
  ].join(",");
  const qs = new URLSearchParams({ select, order: "fecha.desc", limit: String(limit), empresa_id: `eq.${companyId}` });
  const rows = await rest<Record<string, any>[]>(SCHEMA, `gastos?${qs.toString()}`);
  return rows.map(formatGasto);
}

export async function listCategories(companyId: string) {
  const qs = new URLSearchParams({ select: "id,nombre", activo: "eq.true", order: "nombre.asc", empresa_id: `eq.${companyId}` });
  return rest<Array<{ id: string; nombre: string }>>(SCHEMA, `categorias_gasto?${qs.toString()}`);
}

export async function listBankAccounts(companyId?: string) {
  const banksSchema = process.env.BANKS_SCHEMA;
  if (!banksSchema) return [];
  const params: Record<string, string> = {
    select: "id,folio,account_name,bank_name,account_number_mask,current_balance,status",
    status: "eq.active",
    order: "account_name.asc",
    limit: "500"
  };
  if (companyId) params.empresa_id = `eq.${companyId}`;
  const qs = new URLSearchParams(params);
  try {
    return await rest<BankAccount[]>(banksSchema, `banks_accounts?${qs.toString()}`);
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
  const categories = await listCategories(companyId);
  const category = categories.find((item) => item.nombre === input.categoria) || categories[0];
  if (!category) throw new Error("No hay categorias configuradas");
  const dashboardUser = await ensureDashboardUser(user, companyId);
  const folio = await nextFolio(SCHEMA, "gastos", "GAS");
  const account = await accountSnapshot(String(input.cta_retiro_id || ""), companyId);
  const row = {
    folio,
    usuario_id: dashboardUser.id,
    categoria_id: category.id,
    monto: Number(input.monto || 0),
    descripcion: String(input.descripcion || ""),
    fecha: String(input.fecha || new Date().toISOString().slice(0, 10)),
    metodo_captura: "dashboard",
    vehiculo: input.vehiculo || null,
    cta_retiro_id: account?.id || null,
    cta_retiro_folio: account?.folio || null,
    cta_retiro_nombre: account?.account_name || null,
    empresa_id: companyId,
    project_code: "gastos4all",
    module_code: "gastos",
    erp_tags: {}
  };
  const saved = await rest<Record<string, any>[]>(SCHEMA, "gastos", { method: "POST", body: JSON.stringify(row) });
  await writeEvent(saved[0]?.id, dashboardUser.id, "creado", { source: "apps4all", by: user.email }, companyId);
  return formatGasto({ ...saved[0], categorias_gasto: { nombre: category.nombre }, usuarios: { nombre: dashboardUser.nombre } });
}

export async function updateGasto(input: Record<string, any>, user: SessionUser, companyId: string) {
  const folio = String(input.folio || "");
  if (!folio) throw new Error("folio requerido");
  const categories = await listCategories(companyId);
  const category = categories.find((item) => item.nombre === input.categoria);
  const account = await accountSnapshot(String(input.cta_retiro_id || ""), companyId);
  const values: Record<string, any> = {
    monto: Number(input.monto || 0),
    fecha: input.fecha,
    descripcion: input.descripcion || "",
    vehiculo: input.vehiculo || null,
    cta_retiro_id: account?.id || null,
    cta_retiro_folio: account?.folio || null,
    cta_retiro_nombre: account?.account_name || null
  };
  if (category) values.categoria_id = category.id;
  const qs = new URLSearchParams({ folio: `eq.${folio}`, empresa_id: `eq.${companyId}` });
  const rows = await rest<Record<string, any>[]>(SCHEMA, `gastos?${qs.toString()}`, {
    method: "PATCH",
    body: JSON.stringify(values)
  });
  await writeEvent(rows[0]?.id, null, "editado", { source: "apps4all", by: user.email }, companyId);
  return rows[0] || {};
}

export async function deleteGasto(folio: string, user: SessionUser, companyId: string) {
  if (!folio) throw new Error("folio requerido");
  const qs = new URLSearchParams({ folio: `eq.${folio}`, empresa_id: `eq.${companyId}` });
  const existing = await rest<Array<{ id: string }>>(SCHEMA, `gastos?${qs.toString()}&select=id&limit=1`);
  await writeEvent(null, null, "eliminado", { source: "apps4all", by: user.email, folio }, companyId);
  if (existing[0]?.id) {
    const eventQs = new URLSearchParams({ gasto_id: `eq.${existing[0].id}` });
    await rest(SCHEMA, `gasto_eventos?${eventQs.toString()}`, { method: "DELETE" }).catch(() => []);
    await rest(SCHEMA, `gasto_documentos?${eventQs.toString()}`, { method: "DELETE" }).catch(() => []);
  }
  await rest(SCHEMA, `gastos?${qs.toString()}`, { method: "DELETE" });
  return { deleted: true };
}

async function ensureDashboardUser(user: SessionUser, companyId: string) {
  const qs = new URLSearchParams({ telegram_chat_id: "eq.apps4all", select: "id,nombre", limit: "1", empresa_id: `eq.${companyId}` });
  const found = await rest<Array<{ id: string; nombre: string }>>(SCHEMA, `usuarios?${qs.toString()}`);
  if (found[0]) return found[0];
  const row = {
    folio: await nextFolio(SCHEMA, "usuarios", "USR"),
    nombre: "apps4all",
    telegram_chat_id: "apps4all",
    rol: "admin",
    empresa_id: companyId,
    project_code: "gastos4all",
    module_code: "gastos"
  };
  const saved = await rest<Array<{ id: string; nombre: string }>>(SCHEMA, "usuarios", {
    method: "POST",
    body: JSON.stringify(row)
  });
  return saved[0] || { id: "", nombre: user.email };
}

async function accountSnapshot(accountId: string, companyId: string) {
  if (!accountId) return null;
  const rows = await listBankAccounts(companyId);
  return rows.find((row) => row.id === accountId) || null;
}

async function writeEvent(
  gastoId: string | null,
  usuarioId: string | null,
  evento: string,
  detalle: Record<string, any>,
  companyId: string
) {
  const row = {
    folio: await nextFolio(SCHEMA, "gasto_eventos", "EVT"),
    gasto_id: gastoId,
    usuario_id: usuarioId,
    evento,
    detalle,
    empresa_id: companyId,
    project_code: "gastos4all",
    module_code: "gastos"
  };
  await rest(SCHEMA, "gasto_eventos", { method: "POST", body: JSON.stringify(row) }).catch(() => []);
}

async function nextFolio(schema: string, table: string, prefix: string) {
  const qs = new URLSearchParams({ select: "folio", order: "folio.desc", limit: "1" });
  const rows = await rest<Array<{ folio?: string }>>(schema, `${table}?${qs.toString()}`).catch(() => []);
  const last = rows[0]?.folio || `${prefix}-000`;
  const n = Number(String(last).split("-").pop() || "0") + 1;
  return `${prefix}-${String(n).padStart(3, "0")}`;
}

function formatGasto(row: Record<string, any>): Gasto {
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
    categoria: row.categorias_gasto?.nombre || "",
    nombre_usuario: row.usuarios?.nombre || ""
  };
}
