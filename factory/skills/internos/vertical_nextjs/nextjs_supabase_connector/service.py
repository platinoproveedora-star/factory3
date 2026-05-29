from __future__ import annotations

from pathlib import Path


class NextjsSupabaseConnectorService:
    def ejecutar(self, context: dict) -> dict:
        out_dir = Path(context.get("output_dir") or ".")
        files = {
            "lib/supabase.ts": self._supabase(),
            "lib/factoryData.ts": self._factory_data(),
        }
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"files": sorted(files.keys()), "output_dir": str(out_dir)}}

    def _supabase(self) -> str:
        return """import { createClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export const supabase = createClient(url, anonKey);

export async function fetchTable<T>(table: string, select = '*') {
  const { data, error } = await supabase.from(table).select(select);
  if (error) throw error;
  return (data || []) as T[];
}
"""

    def _factory_data(self) -> str:
        return """const factoryApiUrl = process.env.NEXT_PUBLIC_FACTORY_API_URL || '';

export async function fetchFactoryData<T>(skillName: string, params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  const url = `${factoryApiUrl.replace(/\\/$/, '')}/data/${skillName}${query ? `?${query}` : ''}`;
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Factory data error: ${response.status}`);
  return (await response.json()) as T;
}
"""

