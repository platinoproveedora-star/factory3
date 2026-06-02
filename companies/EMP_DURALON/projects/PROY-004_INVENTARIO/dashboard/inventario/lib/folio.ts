const PREFIXES = {
  product: 'PROD',
  customer: 'PTY',
  supplier: 'PTY',
  purchase: 'COM',
  remission: 'REM',
  kardex: 'KAR',
};

export type FolioKind = keyof typeof PREFIXES;

export async function nextFolio(table: string, kind: FolioKind) {
  const prefix = PREFIXES[kind];
  const res = await fetch(`/api/folios?table=${table}&prefix=${prefix}`, { cache: 'no-store' });
  const json = await res.json();
  if (!res.ok || json.ok === false) throw new Error(json.error || 'No se pudo generar folio');
  return json.folio as string;
}
