import { activeSubscription, type SessionUser } from "@/lib/auth";
import { callSkill } from "@/lib/factory";

export const MODULE_CODE = process.env.GPTADS4ALL_MODULE_CODE || "gptads4all";
export const DEFAULT_SCHEMA = process.env.GPTADS4ALL_SCHEMA || "gptads4all";
export const PROJECT_CODE = process.env.GPTADS4ALL_PROJECT_CODE || "PROY-001";

export type ProductBrief = Record<string, any>;
export type IntentSet = { product_key?: string; intents: any[] };
export type ContextHintSet = { product_key?: string; hints: any[] };
export type CampaignDraft = Record<string, any>;
export type CreativeSet = { campaign_key?: string; creatives: any[] };

export function contextFromSession(user: SessionUser) {
  if (!activeSubscription(user.subscription_status)) {
    throw new Error("Modulo sin suscripcion activa");
  }
  return {
    empresa_id: user.company_id,
    company_id: user.company_id,
    project_code: PROJECT_CODE,
    module_code: MODULE_CODE,
    schema: DEFAULT_SCHEMA,
  };
}

export async function buildCampaign(user: SessionUser, input: Record<string, any>) {
  const base = contextFromSession(user);
  const product = await callSkill<{ product_brief: ProductBrief; warnings?: string[] }>(
    "vertical_gptads4all/gptads_product_brief_build",
    {
      ...base,
      dry_run: true,
      product_name: input.product_name,
      description: input.description,
      category: input.category,
      price_range: input.price_range || null,
      url: input.url || null,
      market: {
        country: input.country || "MX",
        language: input.language || "es-MX",
        audience: input.audience || null,
      },
    }
  );
  if (!product.ok || !product.data?.product_brief) throw new Error(product.error || "No se genero ProductBrief");

  const intent = await callSkill<{ intent_set: IntentSet }>("vertical_gptads4all/gptads_intent_research", {
    ...base,
    dry_run: true,
    product_brief: product.data.product_brief,
    max_intents: Number(input.max_intents || 5),
  });
  if (!intent.ok || !intent.data?.intent_set) throw new Error(intent.error || "No se genero IntentSet");

  const hints = await callSkill<{ context_hint_set: ContextHintSet }>("vertical_gptads4all/gptads_context_hints_generate", {
    ...base,
    dry_run: true,
    product_brief: product.data.product_brief,
    intent_set: intent.data.intent_set,
    hints_per_intent: Number(input.hints_per_intent || 1),
  });
  if (!hints.ok || !hints.data?.context_hint_set) throw new Error(hints.error || "No se genero ContextHintSet");

  const campaign = await callSkill<{ campaign_draft: CampaignDraft }>("vertical_gptads4all/gptads_campaign_build", {
    ...base,
    dry_run: false,
    product_brief: product.data.product_brief,
    intent_set: intent.data.intent_set,
    context_hint_set: hints.data.context_hint_set,
    objective: input.objective || "conversions",
    daily_budget_amount: Number(input.daily_budget_amount || 500),
    currency: input.currency || "MXN",
  });
  if (!campaign.ok || !campaign.data?.campaign_draft) throw new Error(campaign.error || "No se guardo CampaignDraft");

  const creative = await callSkill<{ creative_set: CreativeSet; warnings?: string[] }>("vertical_gptads4all/gptads_creative_generate", {
    ...base,
    dry_run: false,
    product_brief: product.data.product_brief,
    intent_set: intent.data.intent_set,
    context_hint_set: hints.data.context_hint_set,
    campaign_draft: campaign.data.campaign_draft,
    variants_per_intent: Number(input.variants_per_intent || 2),
  });
  if (!creative.ok || !creative.data?.creative_set) throw new Error(creative.error || "No se guardaron creativos");

  return {
    product_brief: product.data.product_brief,
    intent_set: intent.data.intent_set,
    context_hint_set: hints.data.context_hint_set,
    campaign_draft: campaign.data.campaign_draft,
    creative_set: creative.data.creative_set,
    warnings: [...(product.data.warnings || []), ...(creative.data.warnings || [])],
  };
}

export async function exportCampaign(user: SessionUser, payload: Record<string, any>) {
  const base = contextFromSession(user);
  const result = await callSkill<any>("vertical_gptads4all/gptads_bulk_export", {
    ...base,
    dry_run: true,
    format: payload.format || "both",
    campaign_draft: payload.campaign_draft,
    creative_set: payload.creative_set,
    intent_set: payload.intent_set,
    context_hint_set: payload.context_hint_set,
  });
  if (!result.ok) throw new Error(result.error || "No se genero export");
  return result.data;
}
