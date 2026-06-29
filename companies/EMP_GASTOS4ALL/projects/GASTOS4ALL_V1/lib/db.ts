import { SCHEMA } from "./constants";

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

function sbEnv() {
  const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos");
  return { url, key };
}

async function sbGet<T>(path: string): Promise<T> {
  const { url, key } = sbEnv();
  const res = await fetch(`${url}/rest/v1/${path}`, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Accept-Profile": SCHEMA,
      Accept: "application/json",
    },
    cache: "no-store",
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`supabase ${res.status}: ${text}`);
  return text ? (JSON.parse(text) as T) : ([] as T);
}

async function sbWrite<T>(path: string, init: RequestInit): Promise<T> {
  const { url, key } = sbEnv();
  const res = await fetch(`${url}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Accept-Profile": SCHEMA,
      "Content-Profile": SCHEMA,
      "Content-Type": "application/json",
      Prefer: "return=representation",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`supabase ${res.status}: ${text}`);
  return text ? (JSON.parse(text) as T) : ([] as T);
}

async function nextFolio(table: string, prefix: string): Promise<string> {
  const qs = new URLSearchParams({ select: "folio", order: "folio.desc", limit: "1" });
  const rows = await sbGet<Array<{ folio?: string }>>(`${table}?${qs}`).catch(() => []);
  const last = rows[0]?.folio || `${prefix}-000`;
  const n = Number(String(last).split("-").pop() || "0") + 1;
  return `${prefix}-${String(n).padStart(3, "0")}`;
}

async function listCategories(empresaId: string) {
  const qs = new URLSearchParams({ select: "id,nombre", empresa_id: `eq.${empresaId}`, activo: "eq.true", order: "nombre.asc" });
  return sbGet<Array<{ id: string; nombre: string }>>(`categorias_gasto?${qs}`);
}

async function ensureDashboardUser(empresaId: string) {
  const qs = new URLSearchParams({ telegram_chat_id: "eq.dashboard", empresa_id: `eq.${empresaId}`, select: "id,nombre", limit: "1" });
  const found = await sbGet<Array<{ id: string; nombre: string }>>(`usuarios?${qs}`);
  if (found[0]) return found[0];
  const row = {
    folio: await nextFolio("usuarios", "USR"),
    nombre: "dashboard",
    telegram_chat_id: "dashboard",
    rol: "admin",
    empresa_id: empresaId,
  };
  const saved = await sbWrite<Array<{ id: string; nombre: string }>>("usuarios", { method: "POST", body: JSON.stringify(row) });
  return saved[0] || { id: "", nombre: "dashboard" };
}

async function writeEvent(empresaId: string, gastoId: string | null, evento: string, detalle: Record<string, any>) {
  const row = {
    folio: await nextFolio("gasto_eventos", "EVT"),
    gasto_id: gastoId,
    usuario_id: null,
    evento,
    detalle,
    empresa_id: empresaId,
  };
  await sbWrite("gasto_eventos", { method: "POST", body: JSON.stringify(row) }).catch(() => []);
}

export async function createGasto(empresaId: string, input: Record<string, any>) {
  const categories = await listCategories(empresaId);
  const category = categories.find((c) => c.nombre === input.categoria) || categories[0];
  if (!category) throw new Error("No hay categorías configuradas");
  const dashboardUser = await ensureDashboardUser(empresaId);
  const folio = await nextFolio("gastos", "GAS");
  const row = {
    folio,
    usuario_id: dashboardUser.id,
    categoria_id: category.id,
    monto: Number(input.monto || 0),
    descripcion: String(input.descripcion || ""),
    fecha: String(input.fecha || new Date().toISOString().slice(0, 10)),
    metodo_captura: "dashboard",
    vehiculo: input.vehiculo || null,
    cta_retiro_id: input.cta_retiro_id || null,
    cta_retiro_folio: input.cta_retiro_folio || null,
    cta_retiro_nombre: input.cta_retiro_nombre || null,
    empresa_id: empresaId,
  };
  const saved = await sbWrite<Record<string, any>[]>("gastos", { method: "POST", body: JSON.stringify(row) });
  await writeEvent(empresaId, saved[0]?.id ?? null, "creado", { source: "gastos4all" });
  return formatGasto({ ...saved[0], categorias_gasto: { nombre: category.nombre }, usuarios: { nombre: dashboardUser.nombre } });
}

export async function updateGasto(empresaId: string, input: Record<string, any>) {
  const folio = String(input.folio || "");
  if (!folio) throw new Error("folio requerido");
  const categories = await listCategories(empresaId);
  const category = categories.find((c) => c.nombre === input.categoria);
  const values: Record<string, any> = {
    monto: Number(input.monto || 0),
    fecha: input.fecha,
    descripcion: input.descripcion || "",
    vehiculo: input.vehiculo || null,
    cta_retiro_id: input.cta_retiro_id || null,
    cta_retiro_folio: input.cta_retiro_folio || null,
    cta_retiro_nombre: input.cta_retiro_nombre || null,
  };
  if (category) values.categoria_id = category.id;
  const qs = new URLSearchParams({ folio: `eq.${folio}`, empresa_id: `eq.${empresaId}` });
  const rows = await sbWrite<Record<string, any>[]>(`gastos?${qs}`, { method: "PATCH", body: JSON.stringify(values) });
  await writeEvent(empresaId, rows[0]?.id ?? null, "editado", { source: "gastos4all" });
  return rows[0] || {};
}

export async function deleteGasto(empresaId: string, folio: string) {
  if (!folio) throw new Error("folio requerido");
  const qs = new URLSearchParams({ folio: `eq.${folio}`, empresa_id: `eq.${empresaId}` });
  const existing = await sbGet<Array<{ id: string }>>(`gastos?${qs}&select=id&limit=1`);
  if (existing[0]?.id) {
    const eventQs = new URLSearchParams({ gasto_id: `eq.${existing[0].id}` });
    await sbWrite(`gasto_eventos?${eventQs}`, { method: "DELETE" }).catch(() => []);
    await sbWrite(`gasto_documentos?${eventQs}`, { method: "DELETE" }).catch(() => []);
  }
  await sbWrite(`gastos?${qs}`, { method: "DELETE" });
  return { deleted: true };
}

function formatGasto(row: Record<string, any>): Gasto {
  return {
    folio: row.folio ?? "",
    fecha: row.fecha ?? "",
    monto: Number(row.monto ?? 0),
    descripcion: row.descripcion ?? "",
    metodo_captura: row.metodo_captura ?? "manual",
    vehiculo: row.vehiculo ?? null,
    cta_retiro_id: row.cta_retiro_id ?? null,
    cta_retiro_folio: row.cta_retiro_folio ?? null,
    cta_retiro_nombre: row.cta_retiro_nombre ?? null,
    categoria: row.categorias_gasto?.nombre ?? "",
    nombre_usuario: row.usuarios?.nombre ?? "",
  };
}

export async function getGastos(empresaId: string, limit = 2000): Promise<Gasto[]> {
  const select = [
    "folio", "fecha", "monto", "descripcion", "metodo_captura", "vehiculo",
    "cta_retiro_id", "cta_retiro_folio", "cta_retiro_nombre",
    "categorias_gasto(nombre)", "usuarios(nombre)",
  ].join(",");
  const qs = new URLSearchParams({
    select,
    empresa_id: `eq.${empresaId}`,
    order: "fecha.desc",
    limit: String(limit),
  });
  const rows = await sbGet<Record<string, any>[]>(`gastos?${qs}`);
  return rows.map(formatGasto);
}

export function calcStats(gastos: Gasto[]): Stats {
  const now = new Date();
  const mes = now.toISOString().slice(0, 7);
  const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().slice(0, 7);

  const total = gastos.reduce((s, g) => s + g.monto, 0);
  const totalMes = gastos.filter((g) => g.fecha.startsWith(mes)).reduce((s, g) => s + g.monto, 0);
  const totalMesAnt = gastos.filter((g) => g.fecha.startsWith(prev)).reduce((s, g) => s + g.monto, 0);
  const variacion = totalMesAnt > 0 ? Math.round(((totalMes - totalMesAnt) / totalMesAnt) * 100) : 0;

  const byCat = new Map<string, { total: number; count: number }>();
  for (const g of gastos) {
    const c = g.categoria || "Sin categoría";
    const cur = byCat.get(c) ?? { total: 0, count: 0 };
    cur.total += g.monto;
    cur.count += 1;
    byCat.set(c, cur);
  }
  const por_categoria = Array.from(byCat.entries())
    .map(([categoria, v]) => ({ categoria, total: v.total, count: v.count }))
    .sort((a, b) => b.total - a.total);

  return {
    total,
    count: gastos.length,
    avg: gastos.length ? total / gastos.length : 0,
    por_categoria,
    totalMes,
    totalMesAnt,
    variacion,
  };
}
