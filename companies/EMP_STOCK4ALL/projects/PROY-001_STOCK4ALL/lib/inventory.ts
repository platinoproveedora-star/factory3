import { SessionUser } from "@/lib/auth";
import { getTenantSource } from "@/lib/platform";
import { callSkill } from "@/lib/factory";

export type InventoryContext = {
  company_id: string;
  schema: string;
  project_code: string;
  module_code: string;
  warehouse_id: string;
};

/**
 * Resuelve la identidad ERP (schema/project_code/module_code) que este
 * usuario debe usar, a partir de platform.tenant_sources. Nunca hardcodea
 * el schema de ningun cliente: cada empresa que activa este modulo tiene
 * su propio tenant_source apuntando a su propio schema/proyecto real.
 */
export async function resolveInventoryContext(
  user: SessionUser,
  warehouseId?: string
): Promise<{ ok: true; data: InventoryContext } | { ok: false; error: string }> {
  const source = await getTenantSource(user.company_id, user.modulo_code);
  if (!source) {
    return { ok: false, error: `Sin tenant_source configurado para ${user.company_id}/${user.modulo_code}` };
  }
  if (!source.source_project_code) {
    return { ok: false, error: "tenant_source sin source_project_code" };
  }

  const resolved = await callSkill<Record<string, any>>("vertical_erp/erp_project_context_resolve", {
    company_id: source.company_id,
    project_code: source.source_project_code
  });
  if (!resolved.ok || !resolved.data) {
    return { ok: false, error: resolved.error || "no se pudo resolver contexto ERP" };
  }
  const schema = resolved.data.schema as string | undefined;
  const moduleCode = resolved.data.module_code as string | undefined;
  if (!schema || !moduleCode) {
    return { ok: false, error: "contexto ERP incompleto (schema/module_code)" };
  }

  return {
    ok: true,
    data: {
      company_id: source.company_id,
      schema,
      project_code: source.source_project_code,
      module_code: moduleCode,
      warehouse_id: (warehouseId || "PRINCIPAL").trim() || "PRINCIPAL"
    }
  };
}
