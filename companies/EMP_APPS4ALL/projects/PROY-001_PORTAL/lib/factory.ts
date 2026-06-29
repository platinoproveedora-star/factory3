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
