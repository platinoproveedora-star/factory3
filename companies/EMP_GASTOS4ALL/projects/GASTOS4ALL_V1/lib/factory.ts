export async function callSkill<T = unknown>(
  skill: string,
  context: Record<string, unknown>
): Promise<{ ok: boolean; data?: T; error?: string }> {
  const base = (process.env.FACTORY_API_URL || "https://factory3.onrender.com").replace(/\/$/, "");
  const res = await fetch(`${base}/skill/${skill}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(context),
    cache: "no-store",
  });
  const json = await res.json().catch(() => ({ ok: false, error: "parse error" }));
  return json as { ok: boolean; data?: T; error?: string };
}

export async function dataSkill<T = unknown>(
  skill: string,
  params: Record<string, unknown>
): Promise<T> {
  const base = (process.env.FACTORY_API_URL || "https://factory3.onrender.com").replace(/\/$/, "");
  const res = await fetch(`${base}/data/${skill}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`factory3 ${res.status}: ${await res.text()}`);
  const json = await res.json();
  if (json?.ok === false) throw new Error(json.error ?? "factory3 error");
  if (json?.ok === true && "data" in json) return json.data as T;
  return json as T;
}
