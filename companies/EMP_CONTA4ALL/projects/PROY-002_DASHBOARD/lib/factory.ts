const FACTORY_URL = process.env.FACTORY_API_URL!;
const FACTORY_SECRET = process.env.FACTORY_API_SECRET!;

export async function callSkill(
  skill: string,
  context: Record<string, unknown>
): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  const res = await fetch(`${FACTORY_URL}/run/${skill}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${FACTORY_SECRET}`,
      "User-Agent": "Conta4all-Dashboard/0.1",
    },
    body: JSON.stringify(context),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    return { ok: false, error: `Factory ${res.status}: ${text}` };
  }
  return res.json();
}
