import { callSkill } from "@/lib/factory";

type SkillMap = Record<string, unknown>;
type Ctx = Record<string, unknown>;

export function companyContext(companyId: string): Ctx {
  return { company_id: companyId };
}

// ── Almacenes ────────────────────────────────────────────────────────────
export async function listWarehouses(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/warehouse_manage", { ...companyContext(companyId), action: "list" });
}

export async function saveWarehouse(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/warehouse_manage", { ...companyContext(companyId), action: "create", ...fields, dry_run: false });
}

// ── Config de la empresa ─────────────────────────────────────────────────
export async function getCompanySettings(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/company_settings_manage", { ...companyContext(companyId), action: "get" });
}

export async function saveCompanySettings(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/company_settings_manage", { ...companyContext(companyId), action: "save", ...fields, dry_run: false });
}

// ── Emisor fiscal ────────────────────────────────────────────────────────
export async function listIssuerProfiles(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/issuer_profile_manage", { ...companyContext(companyId), action: "list" });
}

export async function saveIssuerProfile(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/issuer_profile_manage", { ...companyContext(companyId), action: "create", ...fields, dry_run: false });
}

// ── Clientes / proveedores fiscales ─────────────────────────────────────
export async function listParties(companyId: string, partyType?: string) {
  return callSkill<SkillMap>("vertical_factu4all/party_manage", { ...companyContext(companyId), action: "list", party_type: partyType });
}

export async function saveParty(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/party_manage", { ...companyContext(companyId), action: "create", ...fields, dry_run: false });
}

// ── Productos fiscales ───────────────────────────────────────────────────
export async function listProducts(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/product_manage", { ...companyContext(companyId), action: "list" });
}

export async function saveProduct(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/product_manage", { ...companyContext(companyId), action: "create", ...fields, dry_run: false });
}

// ── Series / folios ──────────────────────────────────────────────────────
export async function listFolioSeries(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/folio_series_manage", { ...companyContext(companyId), action: "list" });
}

export async function saveFolioSeries(companyId: string, fields: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/folio_series_manage", { ...companyContext(companyId), action: "create", ...fields, dry_run: false });
}

// ── Credenciales PAC / CSD (vault) ──────────────────────────────────────
export async function savePacCredentials(companyId: string, pacProvider: string, payload: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/secrets_vault_manage", {
    ...companyContext(companyId),
    action: "store",
    scope_type: "pac_credentials",
    scope_ref: pacProvider,
    payload,
    dry_run: false,
  });
}

export async function pacCredentialsStatus(companyId: string, pacProvider: string) {
  return callSkill<SkillMap>("vertical_factu4all/secrets_vault_manage", {
    ...companyContext(companyId),
    action: "status",
    scope_type: "pac_credentials",
    scope_ref: pacProvider,
  });
}

export async function saveCsd(companyId: string, rfc: string, payload: Ctx) {
  return callSkill<SkillMap>("vertical_factu4all/secrets_vault_manage", {
    ...companyContext(companyId),
    action: "store",
    scope_type: "csd",
    scope_ref: rfc,
    payload,
    dry_run: false,
  });
}

export async function csdStatus(companyId: string, rfc: string) {
  return callSkill<SkillMap>("vertical_factu4all/secrets_vault_manage", {
    ...companyContext(companyId),
    action: "status",
    scope_type: "csd",
    scope_ref: rfc,
  });
}

// ── Facturas ─────────────────────────────────────────────────────────────
export async function listInvoices(companyId: string, direction?: string) {
  return callSkill<SkillMap>("vertical_factu4all/cfdi_document_list", { ...companyContext(companyId), direction });
}

export async function buildInvoice(companyId: string, fields: Ctx, dryRun = false) {
  return callSkill<SkillMap>("vertical_factu4all/cfdi_build", { ...companyContext(companyId), ...fields, dry_run: dryRun });
}

export async function stampInvoice(companyId: string, folio: string) {
  return callSkill<SkillMap>("vertical_factu4all/pac_stamp", { ...companyContext(companyId), folio, dry_run: false });
}

export async function cancelInvoice(companyId: string, folio: string, motivo = "02") {
  return callSkill<SkillMap>("vertical_factu4all/pac_stamp", { ...companyContext(companyId), action: "cancel", folio, motivo });
}

export async function invoiceStatus(companyId: string, folio: string) {
  return callSkill<SkillMap>("vertical_factu4all/pac_stamp", { ...companyContext(companyId), action: "status", folio });
}

export async function downloadInvoiceFile(companyId: string, folio: string, fileType: "xml" | "pdf") {
  return callSkill<SkillMap>("vertical_factu4all/document_download", { ...companyContext(companyId), folio, file_type: fileType });
}

// ── Kardex fiscal ────────────────────────────────────────────────────────
export async function listItemMovements(companyId: string, movementDirection?: string) {
  return callSkill<SkillMap>("vertical_factu4all/cfdi_item_movement_list", { ...companyContext(companyId), movement_direction: movementDirection });
}

export async function listInventoryValuation(companyId: string, environment?: string) {
  return callSkill<SkillMap>("vertical_factu4all/inventory_valuation_list", { ...companyContext(companyId), environment });
}

// ── Egresos (facturas de compra recibidas) ──────────────────────────────
export async function ingestPurchaseInvoice(companyId: string, xml: string, preview: boolean) {
  return callSkill<SkillMap>("vertical_factu4all/purchase_invoice_ingest", { ...companyContext(companyId), xml, dry_run: preview });
}

export async function ingestPurchaseInvoicesBatch(companyId: string, xmls: string[]) {
  return callSkill<SkillMap>("vertical_factu4all/purchase_invoice_ingest", { ...companyContext(companyId), xmls, dry_run: false });
}

export async function listPurchaseInvoices(companyId: string) {
  return callSkill<SkillMap>("vertical_factu4all/cfdi_document_list", { ...companyContext(companyId), direction: "received" });
}
