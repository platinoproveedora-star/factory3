"use client";

import { Download, Loader2, LogOut, Megaphone, Sparkles } from "lucide-react";
import { useState } from "react";

type Result = {
  product_brief: any;
  intent_set: { intents: any[] };
  context_hint_set: { hints: any[] };
  campaign_draft: any;
  creative_set: { creatives: any[] };
  warnings?: string[];
};

const initialForm = {
  product_name: "",
  description: "",
  category: "",
  audience: "",
  country: "MX",
  language: "es-MX",
  objective: "conversions",
  daily_budget_amount: 500,
  currency: "MXN",
  max_intents: 5,
  variants_per_intent: 2,
};

export default function StudioPage() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function generate(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/gptads/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok || !json.ok) {
      setError(json.error || "No se pudo generar la campana");
      return;
    }
    setResult(json.data);
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
              <p className="text-xs text-slate-400">Campaign studio</p>
            </div>
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-slate-300 hover:border-cyan-300 hover:text-cyan-200" title="Salir">
              <LogOut size={18} />
            </button>
          </form>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 xl:grid-cols-[420px_1fr]">
        <form onSubmit={generate} className="rounded-lg border border-white/10 bg-white p-5 text-slate-950 shadow-xl">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Nueva campana</h2>
              <p className="mt-1 text-sm text-slate-500">Genera intenciones, contexto y creativos.</p>
            </div>
            <Sparkles className="text-cyan-600" size={22} />
          </div>

          <div className="space-y-4">
            <Field label="Producto">
              <input className="input" required value={form.product_name} onChange={(event) => setForm({ ...form, product_name: event.target.value })} placeholder="Seguro para flotillas" />
            </Field>
            <Field label="Descripcion">
              <textarea className="input min-h-28 resize-y" required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Que vende, a quien ayuda y por que importa." />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Categoria">
                <input className="input" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} placeholder="Transporte" />
              </Field>
              <Field label="Audiencia">
                <input className="input" value={form.audience} onChange={(event) => setForm({ ...form, audience: event.target.value })} placeholder="Agremiados" />
              </Field>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Pais">
                <input className="input" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value.toUpperCase() })} />
              </Field>
              <Field label="Moneda">
                <input className="input" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} />
              </Field>
              <Field label="Presupuesto">
                <input className="input" type="number" min="1" value={form.daily_budget_amount} onChange={(event) => setForm({ ...form, daily_budget_amount: Number(event.target.value) })} />
              </Field>
            </div>
            <Field label="Objetivo">
              <select className="input" value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })}>
                <option value="conversions">Conversiones</option>
                <option value="leads">Leads</option>
                <option value="traffic">Trafico</option>
              </select>
            </Field>
          </div>

          {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

          <button disabled={loading} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-cyan-700 disabled:opacity-60">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
            {loading ? "Generando..." : "Generar campana"}
          </button>
        </form>

        <section className="min-h-[720px] rounded-lg border border-white/10 bg-slate-900 p-5">
          {!result ? (
            <div className="flex h-full min-h-[560px] items-center justify-center text-center">
              <div className="max-w-md">
                <span className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-lg bg-cyan-400 text-slate-950">
                  <Megaphone size={26} />
                </span>
                <h2 className="mt-5 text-2xl font-semibold">Listo para generar</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">El resultado se guarda en Supabase y queda listo para exportar desde esta pantalla.</p>
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
                      <p className="text-xs font-semibold uppercase text-cyan-300">{intent.intent_id} · {intent.funnel_stage}</p>
                      <p className="mt-2 text-sm text-slate-100">{intent.intent_text}</p>
                    </div>
                  ))}
                </div>
              </Panel>

              <Panel title="Creativos">
                <div className="grid gap-3 lg:grid-cols-2">
                  {(result.creative_set?.creatives || []).map((creative) => (
                    <article key={creative.creative_id} className="rounded-lg border border-white/10 bg-white p-4 text-slate-950">
                      <p className="text-xs font-semibold uppercase text-slate-500">{creative.intent_id} · variante {creative.variant}</p>
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold text-slate-700">{label}</span>
      {children}
    </label>
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
