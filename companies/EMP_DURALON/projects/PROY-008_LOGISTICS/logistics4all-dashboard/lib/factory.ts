export async function callFactory<T = unknown>(
  skill: string,
  context: Record<string, unknown>,
  mode: "data" | "run" = "data"
): Promise<{ ok: boolean; data?: T; error?: string }> {
  const configured = process.env.FACTORY_API_URL;
  if (!configured) {
    return { ok: false, error: "FACTORY_API_URL requerido" };
  }
  const base = configured.replace(/\/$/, "");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (mode === "run" && process.env.FACTORY_RUN_SECRET) {
    headers.Authorization = `Bearer ${process.env.FACTORY_RUN_SECRET}`;
  }
  const res = await fetch(`${base}/${mode}/${skill}`, {
    method: "POST",
    headers,
    body: JSON.stringify(context),
    cache: "no-store"
  });
  const json = await res.json().catch(() => ({ ok: false, error: "parse error" }));
  if (!res.ok || json?.ok === false) {
    return { ok: false, error: json?.detail || json?.error || `Factory error ${res.status}` };
  }
  return { ok: true, data: (json?.data ? json.data : json) as T };
}
