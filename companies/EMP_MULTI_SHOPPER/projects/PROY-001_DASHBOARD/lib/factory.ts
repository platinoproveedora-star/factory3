const FACTORY_URL = (process.env.FACTORY_API_URL || "").replace(/\/$/, "");
const FACTORY_SECRET = process.env.FACTORY_API_SECRET || "";

export type SkillResult<T = unknown> = {
  ok: boolean;
  data?: T;
  error?: string;
};

export function baseContext(extra: Record<string, unknown> = {}) {
  return {
    schema: process.env.MULTI_SHOPPER_SCHEMA || undefined,
    company_id: process.env.MULTI_SHOPPER_COMPANY_ID || undefined,
    empresa_id: process.env.MULTI_SHOPPER_COMPANY_ID || undefined,
    project_code: process.env.MULTI_SHOPPER_PROJECT_CODE || undefined,
    module_code: process.env.MULTI_SHOPPER_MODULE_CODE || undefined,
    ...extra,
  };
}

export async function callSkill<T = unknown>(
  skill: string,
  context: Record<string, unknown>
): Promise<SkillResult<T>> {
  if (!FACTORY_URL) return { ok: false, error: "FACTORY_API_URL requerido" };
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "User-Agent": "MultiShopper-Dashboard/0.1",
  };
  if (FACTORY_SECRET) headers.Authorization = `Bearer ${FACTORY_SECRET}`;

  const res = await fetch(`${FACTORY_URL}/run/${skill}`, {
    method: "POST",
    headers,
    body: JSON.stringify(context),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    return { ok: false, error: `Factory ${res.status}: ${text}` };
  }
  return res.json();
}

export async function dataSkill<T = unknown>(
  skill: string,
  context: Record<string, unknown>
): Promise<SkillResult<T>> {
  if (!FACTORY_URL) return { ok: false, error: "FACTORY_API_URL requerido" };
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "User-Agent": "MultiShopper-Dashboard/0.1",
  };
  const writeKey = process.env.MULTI_SHOPPER_WRITE_KEY || "";
  if (writeKey) headers["x-write-key"] = writeKey;

  const res = await fetch(`${FACTORY_URL}/data/${skill}`, {
    method: "POST",
    headers,
    body: JSON.stringify(context),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    return { ok: false, error: `Factory ${res.status}: ${text}` };
  }
  const data = await res.json();
  return { ok: true, data };
}
