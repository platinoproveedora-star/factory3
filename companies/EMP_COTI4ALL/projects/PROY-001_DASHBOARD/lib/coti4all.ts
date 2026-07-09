import { callSkill } from "@/lib/factory";
import catalogSources from "../catalog_sources.json";

type SkillMap = Record<string, unknown>;
type QuotePdfResult = { html?: string; filename?: string; folio?: string };
type CatalogSource = {
  skill: string;
  schema?: string;
  schema_inventario?: string;
  project_code?: string;
  module_code?: string;
};

export async function getCompanyContextFromSession(user: { company_id: string }) {
  return {
    company_id: user.company_id,
    schema: process.env.COTI4ALL_SCHEMA || "coti4all",
    project_code: process.env.COTI4ALL_PROJECT_CODE || "PROY-001_DASHBOARD",
    module_code: process.env.COTI4ALL_MODULE_CODE || "coti4all_portal",
  };
}

export async function fetchCatalog(context: Record<string, unknown>, priceListCode?: string) {
  const companyId = String(context.company_id || "");
  const source = (catalogSources as Record<string, CatalogSource>)[companyId];
  if (source) {
    const { skill, ...overrides } = source;
    return callSkill<SkillMap>(skill, {
      ...context,
      ...overrides,
      dry_run: false,
    });
  }

  return callSkill<SkillMap>("vertical_coti4all/coti4all_product_catalog", {
    ...context,
    dry_run: false,
    active: true,
    limit: 200,
    price_list_code: priceListCode,
  });
}

export async function saveCatalogItem(context: Record<string, unknown>, item: Record<string, unknown>) {
  return callSkill<SkillMap>("vertical_coti4all/coti4all_product_catalog", { ...context, item, dry_run: true });
}

export async function fetchPriceLists(context: Record<string, unknown>, productId?: string, priceListId?: string) {
  return callSkill<SkillMap>("vertical_coti4all/coti4all_price_list", {
    ...context,
    dry_run: false,
    product_id: productId,
    price_list_id: priceListId,
  });
}

export async function createQuote(context: Record<string, unknown>, quote: Record<string, unknown>, dryRun = true) {
  const normalized = normalizeQuote(quote);
  return callSkill<SkillMap>("vertical_coti4all/coti4all_sales_quote", {
    ...context,
    ...normalized,
    dry_run: dryRun,
  });
}

export async function fetchQuoteDraft(context: Record<string, unknown>, quote: Record<string, unknown>) {
  return createQuote(context, quote, true);
}

export async function fetchQuotePdf(context: Record<string, unknown>, quote: Record<string, unknown>) {
  const quoteId = quote.quote_id || quote.id;
  const folio = quote.folio || quote.external_ref;
  return callSkill<QuotePdfResult>("vertical_coti4all/coti4all_quote_pdf", {
    ...context,
    quote: normalizeQuote(quote),
    quote_id: quoteId,
    folio,
    dry_run: quoteId || folio ? false : true,
  });
}

export async function fetchQuoteList(context: Record<string, unknown>, params: Record<string, unknown> = {}) {
  return callSkill<SkillMap[]>("vertical_coti4all/coti4all_quote_list", {
    ...context,
    dry_run: false,
    ...params,
  });
}

export async function fetchQuoteById(context: Record<string, unknown>, id: string) {
  return callSkill<SkillMap>("vertical_coti4all/coti4all_quote_get", {
    ...context,
    quote_id: id,
    dry_run: false,
  });
}

function normalizeQuote(quote: Record<string, unknown>) {
  const lineas = Array.isArray(quote.lineas) ? quote.lineas : [];
  const items = Array.isArray(quote.items)
    ? quote.items
    : lineas.map((line: any) => ({
        product_code: line.producto_id || line.sku || line.nombre || "ITEM",
        product_name: line.nombre || line.product_name || "",
        quantity: Number(line.cantidad || line.quantity || 0),
        price: Number(line.precio_unitario || line.price || 0),
        unit_cost: Number(line.costo_unitario || line.unit_cost || 0),
        margin_percent: Number(line.margen_porcentaje ?? line.margin_percent ?? line.markup_percent ?? 0),
        unit: line.unidad || line.unit || "PZA",
        notes: line.notas || line.notes || "",
      }));
  const dashboardForm = quote.dashboard_form || {
    empresa_cotiza: quote.empresa_cotiza || "",
    cliente_empresa: quote.cliente_empresa || "",
    cliente_persona: quote.cliente_persona || "",
    obra: quote.obra || "",
    lugar_entrega: quote.lugar_entrega || "",
    nota1: quote.nota1 || "",
    nota2: quote.nota2 || "",
    nota3: quote.nota3 || "",
  };
  return {
    ...quote,
    customer_name: quote.customer_name || quote.cliente_nombre || "",
    customer_email: quote.customer_email || quote.cliente_email || "",
    currency: quote.currency || quote.moneda || "MXN",
    valid_days: quote.valid_days || quote.validez_dias || 30,
    notes: quote.notes || quote.notas || "",
    folio: quote.folio || quote.external_ref || undefined,
    dashboard_form: dashboardForm,
    items,
  };
}
