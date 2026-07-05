import { activeSubscription, type SessionUser } from "@/lib/auth";
import { callSkill } from "@/lib/factory";
import { listGrants } from "@/lib/platform";

export const MODULE_CODE = process.env.GPTADS4ALL_MODULE_CODE || "gptads4all";
export const DEFAULT_SCHEMA = process.env.GPTADS4ALL_SCHEMA || "gptads4all";
export const PROJECT_CODE = process.env.GPTADS4ALL_PROJECT_CODE || "PROY-001";

export type ProductBrief = Record<string, any>;
export type IntentSet = { product_key?: string; intents: any[] };
export type ContextHintSet = { product_key?: string; hints: any[] };
export type CampaignDraft = Record<string, any>;
export type CreativeSet = { campaign_key?: string; creatives: any[] };
export type BriefAnalysis = Record<string, any>;

export async function contextFromSession(user: SessionUser, input: Record<string, any> = {}) {
  if (!activeSubscription(user.subscription_status)) {
    throw new Error("Modulo sin suscripcion activa");
  }
  const selectedCompanyId = String(input.selected_company_id || input.company_id || user.company_id || "").trim();
  const grants = await listGrants(user.sub);
  const hasGptAds = grants.some((grant) => grant.modulo_code === MODULE_CODE && activeSubscription(grant.subscription_status || grant.status));
  const hasCompanyAccess = grants.some((grant) => grant.company_id === selectedCompanyId && activeSubscription(grant.subscription_status || grant.status));
  const allowed = hasGptAds && hasCompanyAccess;
  if (!allowed) throw new Error("Empresa no autorizada para GPTAds4All");
  return {
    empresa_id: selectedCompanyId,
    company_id: selectedCompanyId,
    project_code: PROJECT_CODE,
    module_code: MODULE_CODE,
    schema: DEFAULT_SCHEMA,
  };
}

export async function buildCampaign(user: SessionUser, input: Record<string, any>) {
  const base = await contextFromSession(user, input);
  const analysis = input.brief_analysis && typeof input.brief_analysis === "object" ? input.brief_analysis : null;
  const optimizedDescription = input.optimized_description || analysis?.optimized_description || analysis?.prompt_optimized || input.description;
  const productName = input.product_name || analysis?.product_name;
  const productKey = input.product_key || analysis?.product_key;
  const category = input.category || analysis?.category;
  const audience = input.audience || analysis?.audience;
  const objective = input.objective || analysis?.objective_recommended || "conversions";
  const outputLanguage = input.output_language || analysis?.output_language;
  const marketLanguage = outputLanguage === "en" || outputLanguage === "English" ? "en-US" : outputLanguage === "es" || outputLanguage === "Spanish" ? "es-MX" : input.language;
  const product = await callSkill<{ product_brief: ProductBrief; warnings?: string[] }>(
    "vertical_gptads4all/gptads_product_brief_build",
    {
      ...base,
      dry_run: true,
      product_key: productKey,
      product_name: productName,
      description: optimizedDescription,
      category,
      price_range: input.price_range || null,
      url: input.url || null,
      market: {
        country: input.country || "MX",
        language: marketLanguage || "es-MX",
        audience: audience || null,
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
    objective,
    product_id: input.product_id || analysis?.product_id || null,
    brief_id: input.brief_id || analysis?.brief_id || null,
    brief_analysis: analysis,
    creative_angles_used: analysis?.creative_angles || [],
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
    product_id: input.product_id || analysis?.product_id || null,
    brief_id: input.brief_id || analysis?.brief_id || null,
    variants_per_intent: Number(input.variants_per_intent || 2),
  });
  if (!creative.ok || !creative.data?.creative_set) throw new Error(creative.error || "No se guardaron creativos");

  return {
    product_brief: product.data.product_brief,
    intent_set: intent.data.intent_set,
    context_hint_set: hints.data.context_hint_set,
    campaign_draft: campaign.data.campaign_draft,
    creative_set: creative.data.creative_set,
    brief_analysis: analysis,
    warnings: [...(product.data.warnings || []), ...(creative.data.warnings || [])],
  };
}

export async function analyzeBrief(user: SessionUser, input: Record<string, any>) {
  const base = await contextFromSession(user, input);
  const result = await callSkill<{ brief_analysis: BriefAnalysis; warnings?: string[] }>(
    "vertical_gptads4all/gptads_brief_analyze",
    {
      ...base,
      dry_run: true,
      raw_brief: input.raw_brief || input.description,
      product_key: input.product_key || null,
      product_name: input.product_name || null,
      category: input.category || null,
      output_language: input.output_language || "es",
      daily_budget_amount: input.daily_budget_amount || null,
      currency: input.currency || null,
      market: {
        country: input.country || "US",
        language: input.output_language === "es" ? "es-MX" : input.language || "en-US",
        audience: input.audience || null,
      },
    }
  );
  if (!result.ok || !result.data?.brief_analysis) throw new Error(result.error || "No se pudo analizar el brief");
  const analysis = result.data.brief_analysis;
  const warnings = [...(result.data.warnings || [])];
  let product: any = null;
  let brief: any = null;
  const productSave = await callSkill<any>("vertical_gptads4all/gptads_product_save", {
    ...base,
    dry_run: false,
    product_key: analysis.product_key,
    product_name: analysis.product_name || input.product_name,
    base_brief: input.raw_brief || input.description,
    description: analysis.optimized_description || input.raw_brief || input.description,
    category: analysis.category || input.category,
    market: analysis.market,
    metadata: { source: "brief_analyze", output_language: input.output_language || "es" },
  });
  if (productSave.ok) {
    product = productSave.data?.product || null;
    analysis.product_id = product?.id || null;
    analysis.product_key = product?.product_key || analysis.product_key;
  } else {
    warnings.push(`product_save_failed: ${productSave.error || "unknown"}`);
  }
  const briefSave = await callSkill<any>("vertical_gptads4all/gptads_brief_save", {
    ...base,
    dry_run: false,
    product_id: analysis.product_id,
    product_key: analysis.product_key,
    raw_brief: input.raw_brief || input.description,
    brief_analysis: analysis,
    optimized_description: analysis.optimized_description,
    objective_recommended: analysis.objective_recommended,
    channel_recommended: analysis.channel_recommended,
    quality_score: analysis.quality_score,
    output_language: input.output_language || "es",
    creative_angles: analysis.creative_angles || [],
    missing_fields: analysis.missing_fields || [],
  });
  if (briefSave.ok) {
    brief = briefSave.data?.brief || null;
    analysis.brief_id = brief?.id || null;
  } else {
    warnings.push(`brief_save_failed: ${briefSave.error || "unknown"}`);
  }
  return { brief_analysis: analysis, product, brief, warnings };
}

export async function exportCampaign(user: SessionUser, payload: Record<string, any>) {
  const base = await contextFromSession(user, payload);
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

export async function listLibrary(user: SessionUser, input: Record<string, any>) {
  const base = await contextFromSession(user, input);
  const [products, briefs, history] = await Promise.all([
    callSkill<any>("vertical_gptads4all/gptads_product_list", { ...base, dry_run: false, limit: 100 }),
    callSkill<any>("vertical_gptads4all/gptads_brief_list", { ...base, dry_run: false, product_key: input.product_key || null, limit: 25 }),
    callSkill<any>("vertical_gptads4all/gptads_campaign_history", { ...base, dry_run: false, product_key: input.product_key || null, limit: 25 }),
  ]);
  return {
    products: products.ok ? products.data?.products || [] : [],
    briefs: briefs.ok ? briefs.data?.briefs || [] : [],
    campaigns: history.ok ? history.data?.campaigns || [] : [],
    used_angles: history.ok ? history.data?.used_angles || [] : [],
    warnings: [
      ...(products.ok ? [] : [`products_failed: ${products.error || "unknown"}`]),
      ...(briefs.ok ? [] : [`briefs_failed: ${briefs.error || "unknown"}`]),
      ...(history.ok ? [] : [`history_failed: ${history.error || "unknown"}`]),
    ],
  };
}
