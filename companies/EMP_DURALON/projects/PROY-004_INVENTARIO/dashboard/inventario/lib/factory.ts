const factoryUrl = (process.env.FACTORY_API_URL || 'https://factory3.onrender.com').replace(/\/$/, '');
const writeKey = process.env.FACTORY_WRITE_KEY || '';

export async function runFactorySkill<T>(skill: string, context: Record<string, any>): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (writeKey) headers['X-Write-Key'] = writeKey;
  const res = await fetch(`${factoryUrl}/data/${skill}`, {
    method: 'POST',
    headers,
    cache: 'no-store',
    body: JSON.stringify({
      company_id: 'EMP_DURALON',
      project_code: 'PROY-004',
      module_code: 'inventario',
      schema: 'uc101_proy004',
      dry_run: false,
      ...context,
    }),
  });
  const json = await res.json();
  if (!res.ok || json?.ok === false) {
    throw new Error(json?.detail || json?.error || `Factory error ${res.status}`);
  }
  return json as T;
}
