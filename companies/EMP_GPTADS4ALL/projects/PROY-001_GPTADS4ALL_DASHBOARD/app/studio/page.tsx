"use client";

import { ClipboardCheck, Download, Loader2, LogOut, Megaphone, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";

type Analysis = {
  product_name?: string;
  category?: string;
  audience?: string;
  objective_recommended?: string;
  objective_reason?: string;
  channel_recommended?: string;
  cta_recommended?: string;
  differentiators?: string[];
  objections?: string[];
  creative_angles?: string[];
  missing_fields?: string[];
  quality_score?: number;
  optimized_description?: string;
  prompt_optimized?: string;
  output_language?: string;
};

type Result = {
  product_brief: any;
  intent_set: { intents: any[] };
  context_hint_set: { hints: any[] };
  campaign_draft: any;
  creative_set: { creatives: any[] };
  brief_analysis?: Analysis;
  warnings?: string[];
};

const initialForm = {
  selected_company_id: "",
  product_key: "",
  product_id: "",
  brief_id: "",
  raw_brief: "",
  product_name: "",
  category: "",
  audience: "",
  country: "US",
  language: "en-US",
  output_language: "es",
  objective: "leads",
  daily_budget_amount: 50,
  currency: "USD",
  max_intents: 5,
  variants_per_intent: 2,
};

export default function StudioPage() {
  const [form, setForm] = useState(initialForm);
  const [companies, setCompanies] = useState<any[]>([]);
  const [sessionUser, setSessionUser] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [briefs, setBriefs] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [usedAngles, setUsedAngles] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetch("/api/auth/grants/me")
      .then((res) => res.json())
      .then((json) => {
        const rows = Array.isArray(json.companies) ? json.companies : [];
        setSessionUser(json.user || null);
        setCompanies(rows);
        const current = json.user?.company_id || rows[0]?.company_id || "";
        setForm((prev) => ({ ...prev, selected_company_id: prev.selected_company_id || current }));
      })
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!form.selected_company_id) return;
    loadLibrary(form.selected_company_id, form.product_key);
  }, [form.selected_company_id, form.product_key]);

  async function loadLibrary(companyId: string, productKey = "") {
    const res = await fetch("/api/gptads/library", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_company_id: companyId, product_key: productKey || null }),
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok || !json.ok) return;
    setProducts(json.data?.products || []);
    setBriefs(json.data?.briefs || []);
    setCampaigns(json.data?.campaigns || []);
    setUsedAngles(json.data?.used_angles || []);
  }

  function selectProduct(productKey: string) {
    const product = products.find((item) => item.product_key === productKey);
    setAnalysis(null);
    setResult(null);
    setForm({
      ...form,
      product_key: product?.product_key || "",
      product_id: product?.id || "",
      product_name: product?.product_name || "",
      category: product?.category || "",
      raw_brief: product?.base_brief || product?.description || "",
    });
  }

  async function analyze(event: React.FormEvent) {
    event.preventDefault();
    setAnalyzing(true);
    setError("");
    setNotice("");
    setResult(null);
    const res = await fetch("/api/gptads/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const json = await res.json().catch(() => ({}));
    setAnalyzing(false);
    if (!res.ok || !json.ok) {
      setError(json.error || "No se pudo analizar el brief");
      return;
    }
    const nextAnalysis = json.data?.brief_analysis || null;
    const savedProduct = json.data?.product || null;
    const savedBrief = json.data?.brief || null;
    const warnings = Array.isArray(json.data?.warnings) ? json.data.warnings : [];
    const saved = [
      savedProduct?.id ? `Producto guardado: ${savedProduct.product_name || savedProduct.product_key}` : "",
      savedBrief?.id ? `Brief guardado: ${savedBrief.folio || savedBrief.id}` : "",
    ].filter(Boolean);
    setNotice([...saved, ...warnings].join(" | "));
    setAnalysis(nextAnalysis);
    setForm({
      ...form,
      product_key: savedProduct?.product_key || nextAnalysis?.product_key || form.product_key,
      product_id: savedProduct?.id || nextAnalysis?.product_id || form.product_id,
      brief_id: savedBrief?.id || nextAnalysis?.brief_id || form.brief_id,
      product_name: nextAnalysis?.product_name || form.product_name,
      category: nextAnalysis?.category || form.category,
      audience: nextAnalysis?.audience || form.audience,
      objective: nextAnalysis?.objective_recommended || form.objective,
      output_language: nextAnalysis?.output_language === "English" ? "en" : form.output_language,
    });
    if (form.selected_company_id) loadLibrary(form.selected_company_id, savedProduct?.product_key || nextAnalysis?.product_key || form.product_key);
  }

  async function generate() {
    setLoading(true);
    setError("");
    setNotice("");
    const res = await fetch("/api/gptads/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        description: analysis?.optimized_description || form.raw_brief,
        optimized_description: analysis?.optimized_description,
        brief_analysis: analysis,
      }),
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok || !json.ok) {
      setError(json.error || "No se pudo generar la campana");
      return;
    }
    setResult(json.data);
    if (form.selected_company_id) loadLibrary(form.selected_company_id, form.product_key);
  }

  async function exportFile(format: "csv" | "json") {
    if (!result) return;
    setExporting(true);
    setError("");
    const res = await fetch("/api/gptads/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...result, format }),
    });
    const json = await res.json().catch(() => ({}));
    setExporting(false);
    if (!res.ok || !json.ok) {
      setError(json.error || "No se pudo exportar");
      return;
    }
    const content = json.data?.content?.[format];
    if (!content) {
      setError("Export vacio");
      return;
    }
    const blob = new Blob([content], { type: format === "csv" ? "text/csv;charset=utf-8" : "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.campaign_draft?.campaign_key || "gptads4all"}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-slate-950/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-400 text-slate-950">
              <Megaphone size={20} />
            </span>
            <div>
              <h1 className="text-lg font-semibold">GPTAds4All</h1>
              <p className="text-xs text-slate-400">
                {sessionUser?.email ? `Sesion: ${sessionUser.email}` : "Campaign studio"}
              </p>
            </div>
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-slate-300 hover:border-cyan-300 hover:text-cyan-200" title="Salir">
              <LogOut size={18} />
            </button>
          </form>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 xl:grid-cols-[460px_1fr]">
        <section className="rounded-lg border border-white/10 bg-white p-5 text-slate-950 shadow-xl">
          <form onSubmit={analyze}>
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Brief general</h2>
                <p className="mt-1 text-sm text-slate-500">Cuenta todo lo que sepas. La app prepara el prompt antes de generar.</p>
              </div>
              <ClipboardCheck className="text-cyan-600" size={22} />
            </div>

            <div className="space-y-4">
              <Field label="Empresa">
                <select className="input" value={form.selected_company_id} onChange={(event) => setForm({ ...form, selected_company_id: event.target.value, product_key: "", product_id: "", brief_id: "" })}>
                  {companies.map((company) => (
                    <option key={company.company_id} value={company.company_id}>{company.name || company.company_id}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-500">
                  Se guarda en esta empresa con tu sesion activa. ADMINTOTAL puede ver varias empresas por sus grants.
                </p>
              </Field>
              <Field label="Producto guardado">
                <select className="input" value={form.product_key} onChange={(event) => selectProduct(event.target.value)}>
                  <option value="">Nuevo producto</option>
                  {products.map((product) => (
                    <option key={product.product_key} value={product.product_key}>{product.product_name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Producto">
                <input className="input" value={form.product_name} onChange={(event) => setForm({ ...form, product_name: event.target.value })} placeholder="Cafe organico chiapaneco 500g" />
              </Field>
              <Field label="Descripcion general">
                <textarea
                  className="input min-h-56 resize-y"
                  required
                  value={form.raw_brief}
                  onChange={(event) => setForm({ ...form, raw_brief: event.target.value })}
                  placeholder={"Incluye si puedes: que vendes, para quien es, precio, zona, canal de contacto, diferenciadores, objeciones, promociones, temporada y tono de marca."}
                />
              </Field>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Pais">
                  <select className="input" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value, language: event.target.value === "US" && form.output_language === "en" ? "en-US" : "es-MX" })}>
                    <option value="MX">Mexico</option>
                    <option value="US">USA</option>
                  </select>
                </Field>
                <Field label="Moneda">
                  <select className="input" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })}>
                    <option value="MXN">Pesos mexicanos</option>
                    <option value="USD">US dollar</option>
                  </select>
                </Field>
                <Field label="Budget">
                  <input className="input" type="number" min="1" value={form.daily_budget_amount} onChange={(event) => setForm({ ...form, daily_budget_amount: Number(event.target.value) })} />
                </Field>
              </div>
              <Field label="Idioma del resultado">
                <div className="grid grid-cols-2 gap-2">
                  <button type="button" onClick={() => setForm({ ...form, output_language: "es", language: "es-MX" })} className={form.output_language === "es" ? "choice-active" : "choice"}>
                    Español
                  </button>
                  <button type="button" onClick={() => setForm({ ...form, output_language: "en", language: "en-US" })} className={form.output_language === "en" ? "choice-active" : "choice"}>
                    English
                  </button>
                </div>
              </Field>
            </div>

            {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            {notice && <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{notice}</p>}

            <button disabled={analyzing} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-cyan-700 disabled:opacity-60">
              {analyzing ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
              {analyzing ? "Analizando..." : "Analizar y preparar campana"}
            </button>
          </form>

          {analysis && (
            <div className="mt-5 space-y-4 border-t border-slate-200 pt-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Objetivo recomendado">
                  <select className="input" value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })}>
                    <option value="leads">Leads</option>
                    <option value="conversions">Conversiones</option>
                    <option value="traffic">Trafico</option>
                  </select>
                </Field>
                <Field label="Categoria">
                  <input className="input" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
                </Field>
              </div>
              <Field label="Audiencia detectada">
                <input className="input" value={form.audience} onChange={(event) => setForm({ ...form, audience: event.target.value })} />
              </Field>
              <AnalysisBox analysis={analysis} />
              <LibraryBox briefs={briefs} campaigns={campaigns} usedAngles={usedAngles} />
              <button type="button" disabled={loading} onClick={generate} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 px-4 py-3 text-sm font-semibold text-white hover:bg-cyan-700 disabled:opacity-60">
                {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
                {loading ? "Generando..." : "Generar campana"}
              </button>
            </div>
          )}
        </section>

        <section className="min-h-[720px] rounded-lg border border-white/10 bg-slate-900 p-5">
          {!result ? (
            <div className="flex h-full min-h-[560px] items-center justify-center text-center">
              <div className="max-w-md">
                <span className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-lg bg-cyan-400 text-slate-950">
                  <Megaphone size={26} />
                </span>
                <h2 className="mt-5 text-2xl font-semibold">Primero analiza el brief</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">La app detecta objetivo, canal, faltantes y angulos antes de guardar la campana.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-col gap-3 border-b border-white/10 pb-5 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase text-cyan-300">{result.campaign_draft?.campaign_key}</p>
                  <h2 className="mt-1 text-2xl font-semibold">{result.campaign_draft?.campaign_name}</h2>
                </div>
                <div className="flex gap-2">
                  <button disabled={exporting} onClick={() => exportFile("csv")} className="btn-dark"><Download size={16} /> CSV</button>
                  <button disabled={exporting} onClick={() => exportFile("json")} className="btn-dark"><Download size={16} /> JSON</button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Intenciones" value={result.intent_set?.intents?.length || 0} />
                <Metric label="Hints" value={result.context_hint_set?.hints?.length || 0} />
                <Metric label="Creativos" value={result.creative_set?.creatives?.length || 0} />
                <Metric label="Objetivo" value={result.campaign_draft?.objective || "-"} />
              </div>

              {result.brief_analysis && (
                <Panel title="Analisis usado">
                  <p className="text-sm leading-6 text-slate-300">{result.brief_analysis.objective_reason}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Tag>Canal: {result.brief_analysis.channel_recommended || "-"}</Tag>
                    <Tag>CTA: {result.brief_analysis.cta_recommended || "-"}</Tag>
                    <Tag>Score: {result.brief_analysis.quality_score || "-"}</Tag>
                  </div>
                </Panel>
              )}

              <Panel title="Product brief">
                <p className="text-sm leading-6 text-slate-300">{result.product_brief?.description}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(result.product_brief?.value_props || []).map((item: string) => <Tag key={item}>{item}</Tag>)}
                </div>
              </Panel>

              <Panel title="Intenciones">
                <div className="grid gap-3 md:grid-cols-2">
                  {(result.intent_set?.intents || []).map((intent) => (
                    <div key={intent.intent_id} className="rounded-lg border border-white/10 bg-slate-950 p-4">
                      <p className="text-xs font-semibold uppercase text-cyan-300">{intent.intent_id} - {intent.funnel_stage}</p>
                      <p className="mt-2 text-sm text-slate-100">{intent.intent_text}</p>
                    </div>
                  ))}
                </div>
              </Panel>

              <Panel title="Creativos">
                <div className="grid gap-3 lg:grid-cols-2">
                  {(result.creative_set?.creatives || []).map((creative) => (
                    <article key={creative.creative_id} className="rounded-lg border border-white/10 bg-white p-4 text-slate-950">
                      <p className="text-xs font-semibold uppercase text-slate-500">{creative.intent_id} - variante {creative.variant}</p>
                      <h3 className="mt-2 text-lg font-semibold">{creative.headline}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{creative.body}</p>
                      <p className="mt-3 inline-flex rounded-md bg-cyan-50 px-2 py-1 text-xs font-semibold text-cyan-800">{creative.cta}</p>
                    </article>
                  ))}
                </div>
              </Panel>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function AnalysisBox({ analysis }: { analysis: Analysis }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Mini label="Canal" value={analysis.channel_recommended || "-"} />
        <Mini label="CTA" value={analysis.cta_recommended || "-"} />
        <Mini label="Score" value={analysis.quality_score || "-"} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{analysis.objective_reason}</p>
      <List title="Angulos" items={analysis.creative_angles || []} />
      <List title="Falta para mejorar" items={analysis.missing_fields || []} empty="Sin faltantes criticos" />
    </div>
  );
}

function LibraryBox({ briefs, campaigns, usedAngles }: { briefs: any[]; campaigns: any[]; usedAngles: string[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Mini label="Briefs" value={briefs.length} />
        <Mini label="Campanas" value={campaigns.length} />
        <Mini label="Angulos usados" value={usedAngles.length} />
      </div>
      <List title="Angulos ya usados" items={usedAngles.slice(0, 8)} empty="Aun no hay historial para este producto" />
      {campaigns.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase text-slate-500">Historial reciente</p>
          <div className="mt-2 space-y-2">
            {campaigns.slice(0, 3).map((campaign) => (
              <div key={campaign.id || campaign.campaign_key} className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-700">
                <p className="font-semibold text-slate-900">{campaign.campaign_name || campaign.campaign_key}</p>
                <p>{campaign.objective || "-"} · {campaign.status || "draft"}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold text-slate-700">{label}</span>
      {children}
    </label>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <p className="text-[11px] font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function List({ title, items, empty }: { title: string; items: string[]; empty?: string }) {
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{title}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.length ? items.map((item) => <span key={item} className="rounded-md bg-white px-2 py-1 text-xs text-slate-700">{item}</span>) : <span className="text-xs text-slate-500">{empty || "-"}</span>}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950 p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-white/10 bg-slate-950 p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase text-slate-400">{title}</h3>
      {children}
    </section>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">{children}</span>;
}
