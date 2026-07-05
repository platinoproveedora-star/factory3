export async function callSkill<T = unknown>(
  skill: string,
  context: Record<string, unknown>
): Promise<{ ok: boolean; data?: T; error?: string }> {
  const base = (process.env.FACTORY_API_URL || "").replace(/\/$/, "");
  if (!base) return { ok: false, error: "FACTORY_API_URL no configurado" };
  const secret = process.env.FACTORY_RUN_SECRET || "";
  if (!secret) return { ok: false, error: "FACTORY_RUN_SECRET no configurado" };
  const res = await fetch(`${base}/run/${encodeURIComponent(skill)}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(context),
    cache: "no-store",
  });
  const json = await res.json().catch(() => ({ ok: false, error: "parse error" }));
  if (!res.ok || json?.ok === false) {
    return { ok: false, error: (json as any)?.detail || (json as any)?.error || `Factory error ${res.status}` };
  }
  return { ok: true, data: ((json as any)?.data ?? json ?? {}) as T };
}
