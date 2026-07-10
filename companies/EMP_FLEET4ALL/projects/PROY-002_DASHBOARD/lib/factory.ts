const FACTORY_URL = process.env.FACTORY_API_URL!;
const FACTORY_SECRET = process.env.FACTORY_API_SECRET!;
const FACTORY_TIMEOUT_MS = Number(process.env.FACTORY_API_TIMEOUT_MS || 30000);

export async function callSkill(
  skill: string,
  context: Record<string, unknown>
): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FACTORY_TIMEOUT_MS);
  try {
    const res = await fetch(`${FACTORY_URL}/run/${skill}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${FACTORY_SECRET}`,
        "User-Agent": "Fleet4All-Dashboard/0.1",
      },
      body: JSON.stringify(context),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      return { ok: false, error: `Factory ${res.status}: ${text}` };
    }
    return res.json();
  } catch (error) {
    const message = error instanceof Error && error.name === "AbortError"
      ? `Factory timeout despues de ${Math.round(FACTORY_TIMEOUT_MS / 1000)}s`
      : error instanceof Error
        ? error.message
        : "Error de conexion con Factory";
    return { ok: false, error: message };
  } finally {
    clearTimeout(timer);
  }
}
