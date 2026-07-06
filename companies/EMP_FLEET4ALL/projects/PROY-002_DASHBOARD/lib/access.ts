import { listGrants } from "@/lib/platform";

const MODULE_CODE = "fleet4all";

/**
 * Verifica que el usuario tenga un grant activo (active/trialing/manual/comped)
 * sobre modulo_code=fleet4all para la empresa (company_id) solicitada.
 * listGrants ya filtra por status valido; aqui solo validamos modulo_code + company_id.
 */
export async function requireFleetCompanyAccess(userId: string, empresaId: string): Promise<boolean> {
  if (!userId || !empresaId) return false;
  try {
    const grants = await listGrants(userId);
    return grants.some((grant) => grant.modulo_code === MODULE_CODE && grant.company_id === empresaId);
  } catch {
    return false;
  }
}
