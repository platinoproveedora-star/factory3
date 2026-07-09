"use client";

import Link from "next/link";
import {
  ChevronRight,
  FileText,
  ListOrdered,
  Loader2,
  LogOut,
  PackagePlus,
  Pencil,
  PlusCircle,
  ReceiptText,
  Settings,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";

type Producto = {
  id: string;
  nombre?: string;
  sku?: string;
  precio?: number;
  costo?: number;
  costo_referencia?: number;
  list_price_base?: number;
  product_name?: string;
  product_code?: string;
  moneda?: string;
  currency?: string;
  unit?: string;
  unidad?: string;
};

type Linea = {
  producto_id?: string;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  costo_unitario: number;
  margen_porcentaje?: number;
  unidad: string;
};

const UNIDAD_PRESETS = ["KG", "TON", "BULTO", "PZA"];
const DEFAULT_MARGIN_PERCENT = 15;

type Cotizacion = {
  id?: string;
  folio?: string;
  empresa_cotiza: string;
  cliente_empresa: string;
  cliente_persona: string;
  obra: string;
  lugar_entrega: string;
  nota1: string;
  nota2: string;
  nota3: string;
  moneda: string;
  validez_dias: number;
  lineas: Linea[];
};

type CompanyOption = {
  company_id: string;
  name: string;
  status?: string;
};

type SavedClient = Pick<Cotizacion, "cliente_empresa" | "cliente_persona" | "obra" | "lugar_entrega" | "nota1" | "nota2" | "nota3"> & {
  id: string;
  updated_at: string;
};

type SavedQuoteCompany = {
  id: string;
  empresa_cotiza: string;
  updated_at: string;
};

type QuoteListRow = {
  id: string;
  folio: string;
  client_nombre?: string;
  status?: string;
  moneda?: string;
  total?: number;
  created_at?: string;
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const portalHref = process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018";
const MODULE_CODE = "coti4all_portal";
const IVA_RATE = 0.16;

function roundMoney(value: number) {
  return Math.round((Number(value) || 0) * 100) / 100;
}

function priceFromCostAndMargin(cost: number, marginPercent: number) {
  return roundMoney((Number(cost) || 0) * (1 + (Number(marginPercent) || 0) / 100));
}

function marginFromCostAndPrice(cost: number, price: number) {
  const base = Number(cost) || 0;
  if (!base) return 0;
  return Math.round((((Number(price) || 0) - base) / base) * 10000) / 100;
}

function lineMarginPercent(line: Linea) {
  if (typeof line.margen_porcentaje === "number" && Number.isFinite(line.margen_porcentaje)) return line.margen_porcentaje;
  return marginFromCostAndPrice(line.costo_unitario, line.precio_unitario);
}

export default function CotizadorPage() {
  const [mounted, setMounted] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [auth, setAuth] = useState<Record<string, unknown>>({});
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [loading, setLoading] = useState(false);
  const [catalogo, setCatalogo] = useState<Producto[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [savedClients, setSavedClients] = useState<SavedClient[]>([]);
  const [savedQuoteCompanies, setSavedQuoteCompanies] = useState<SavedQuoteCompany[]>([]);
  const [clientSaveStatus, setClientSaveStatus] = useState("");
  const [quoteCompanySaveStatus, setQuoteCompanySaveStatus] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [catalogCompanyId, setCatalogCompanyId] = useState("");
  const [catalogStatus, setCatalogStatus] = useState("Selecciona empresa para cargar catálogo.");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogVisibleCount, setCatalogVisibleCount] = useState(30);
  const [bulkMarginPercent, setBulkMarginPercent] = useState(DEFAULT_MARGIN_PERCENT);
  const [saveStatus, setSaveStatus] = useState("");
  const [savingQuote, setSavingQuote] = useState(false);
  const [quotes, setQuotes] = useState<QuoteListRow[]>([]);
  const [quotesLoading, setQuotesLoading] = useState(false);
  const [quotesError, setQuotesError] = useState("");
  const [form, setForm] = useState<Cotizacion>({
    empresa_cotiza: "",
    cliente_empresa: "",
    cliente_persona: "",
    obra: "",
    lugar_entrega: "",
    nota1: "",
    nota2: "",
    nota3: "",
    moneda: "MXN",
    validez_dias: 30,
    lineas: [],
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    fetch("/api/auth/grants/me")
      .then(async (res) => {
        if (!res.ok) return;
        const json = await res.json();
        setAuth(json.user || {});
        const grants = Array.isArray(json.grants) ? json.grants : [];
        const allowedCompanyIds = new Set(
          grants
            .filter((grant: any) => grant.modulo_code === MODULE_CODE)
            .map((grant: any) => String(grant.company_id || ""))
            .filter(Boolean)
        );
        const allCompanies = Array.isArray(json.companies) ? json.companies : [];
        const companyRows = allCompanies.filter((company: CompanyOption) => allowedCompanyIds.has(company.company_id));
        setCompanies(companyRows);
        const initialCompany = String(
          companyRows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
            companyRows[0]?.company_id ||
            json.user?.company_id ||
            ""
        );
        setSelectedCompanyId((current) => current || initialCompany);
        setCatalogCompanyId((current) => current || initialCompany);
      })
      .catch(() => {})
      .finally(() => setAuthLoading(false));
  }, [mounted]);

  useEffect(() => {
    if (!catalogCompanyId) return;
    setCatalogStatus("Cargando catálogo...");
    setCatalogo([]);
    setCatalogSearch("");
    setCatalogVisibleCount(30);
    const q = new URLSearchParams({
      company_id: catalogCompanyId,
    });
    fetch(`/api/cotizador?${q}`)
      .then(async (res) => {
        if (!res.ok) {
          setCatalogStatus("No hay catálogo conectado para esta empresa todavía.");
          return;
        }
        const json = await res.json();
        const products = json.catalogo?.products || json.catalogo || [];
        setCatalogo(products);
        setCatalogStatus(products.length ? `${products.length} productos disponibles.` : "Sin productos para esta empresa.");
      })
      .catch(() => setCatalogStatus("No se pudo cargar el catálogo."));
  }, [catalogCompanyId]);

  const totals = form.lineas.reduce(
    (acc, line) => {
      const costo = line.cantidad * (line.costo_unitario || 0);
      const importe = line.cantidad * line.precio_unitario;
      const margen = importe - costo;
      return {
        subtotal: acc.subtotal + importe,
        costoSubtotal: acc.costoSubtotal + costo,
        margenSubtotal: acc.margenSubtotal + margen,
      };
    },
    { subtotal: 0, costoSubtotal: 0, margenSubtotal: 0 }
  );
  const iva = totals.subtotal * IVA_RATE;
  const total = totals.subtotal + iva;
  const costoIva = totals.costoSubtotal * IVA_RATE;
  const costoTotal = totals.costoSubtotal + costoIva;
  const margenIva = totals.margenSubtotal * 0;
  const margenTotal = totals.margenSubtotal + margenIva;
  const selectedCompany = companies.find((company) => company.company_id === selectedCompanyId);
  const clientStorageKey = `coti4all_clients:${String(auth.sub || auth.email || "local")}`;
  const quoteCompanyStorageKey = `coti4all_quote_companies:${String(auth.sub || auth.email || "local")}`;
  const documentPayload = {
    ...form,
    company_id: selectedCompanyId,
    cliente_nombre: form.cliente_persona,
    customer_name: form.cliente_persona,
    customer_company: form.cliente_empresa,
    notes: [form.nota1, form.nota2, form.nota3].filter(Boolean).join("\n"),
  };
  const savePayload = {
    ...documentPayload,
    folio: form.folio,
    dashboard_form: {
      empresa_cotiza: form.empresa_cotiza,
      cliente_empresa: form.cliente_empresa,
      cliente_persona: form.cliente_persona,
      obra: form.obra,
      lugar_entrega: form.lugar_entrega,
      nota1: form.nota1,
      nota2: form.nota2,
      nota3: form.nota3,
    },
  };

  const loadQuotes = () => {
    if (!selectedCompanyId) return;
    setQuotesLoading(true);
    setQuotesError("");
    fetch(`/api/cotizador/quotes?company_id=${encodeURIComponent(selectedCompanyId)}`)
      .then(async (res) => {
        const json = await res.json();
        if (!res.ok || !json.ok) throw new Error(json.error || "No se pudieron cargar las cotizaciones");
        setQuotes(Array.isArray(json.data) ? json.data : []);
      })
      .catch((err) => setQuotesError((err as Error).message))
      .finally(() => setQuotesLoading(false));
  };

  useEffect(() => {
    if (step === 4) loadQuotes();
  }, [step, selectedCompanyId]);

  const saveQuote = async () => {
    if (!form.lineas.length) {
      setSaveStatus("Agrega al menos un renglon antes de guardar.");
      return;
    }
    setSavingQuote(true);
    setSaveStatus("");
    try {
      const res = await fetch("/api/cotizador/quotes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savePayload),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) throw new Error(json.error || "No se pudo guardar la cotizacion");
      const folio = json.data?.folio;
      const quoteId = json.data?.quote_id;
      if (folio) setForm((current) => ({ ...current, folio, id: quoteId || current.id }));
      setSaveStatus(folio ? `Cotizacion guardada: ${folio}` : "Cotizacion guardada.");
      if (step === 4) loadQuotes();
    } catch (err) {
      setSaveStatus((err as Error).message);
    } finally {
      setSavingQuote(false);
    }
  };

  const editQuote = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/cotizador/quotes/${id}?company_id=${encodeURIComponent(selectedCompanyId)}`);
      const json = await res.json();
      if (!res.ok || !json.ok) throw new Error(json.error || "No se pudo cargar la cotizacion");
      const quote = json.data?.quote || {};
      const items = Array.isArray(json.data?.items) ? json.data.items : [];
      const df = json.data?.dashboard_form || {};
      const metadataItems = Array.isArray(quote.metadata?.items) ? quote.metadata.items : [];
      setForm({
        id: quote.id,
        folio: quote.folio,
        empresa_cotiza: df.empresa_cotiza || "",
        cliente_empresa: df.cliente_empresa || "",
        cliente_persona: df.cliente_persona || quote.client_nombre || "",
        obra: df.obra || "",
        lugar_entrega: df.lugar_entrega || "",
        nota1: df.nota1 || "",
        nota2: df.nota2 || "",
        nota3: df.nota3 || "",
        moneda: quote.moneda || "MXN",
        validez_dias: Number(quote.validez_dias || 30),
        lineas: items.map((it: any, idx: number) => {
          const meta = metadataItems[idx] || {};
          const cost = Number(it.costo_unitario || 0);
          const price = Number(it.precio_unitario || 0);
          return {
            nombre: it.nombre || it.sku || "Producto",
            cantidad: Number(it.cantidad || 0),
            precio_unitario: price,
            costo_unitario: cost,
            margen_porcentaje: Number(meta.margin_percent ?? meta.margen_porcentaje ?? it.margen_porcentaje ?? marginFromCostAndPrice(cost, price)),
            unidad: it.unidad || "PZA",
          };
        }),
      });
      setSaveStatus(`Editando ${quote.folio || ""}`);
      setStep(1);
    } catch (err) {
      setQuotesError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!clientStorageKey) return;
    try {
      const parsed = JSON.parse(localStorage.getItem(clientStorageKey) || "[]");
      setSavedClients(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSavedClients([]);
    }
  }, [clientStorageKey]);

  useEffect(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem(quoteCompanyStorageKey) || "[]");
      setSavedQuoteCompanies(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSavedQuoteCompanies([]);
    }
  }, [quoteCompanyStorageKey]);

  const addManualLine = () => {
    setForm((current) => ({
      ...current,
      lineas: [
        ...current.lineas,
        { nombre: "", cantidad: 1, precio_unitario: 0, costo_unitario: 0, margen_porcentaje: bulkMarginPercent, unidad: "PZA" },
      ],
    }));
  };

  const addProduct = (product: Producto) => {
    const name = product.nombre || product.product_name || product.sku || product.product_code || "Producto";
    const cost = Number(product.costo ?? product.costo_referencia ?? 0);
    const price = priceFromCostAndMargin(cost, bulkMarginPercent);
    const unidad = String(product.unit || product.unidad || "PZA").toUpperCase();
    setForm((current) => ({
      ...current,
      lineas: [
        ...current.lineas,
        {
          producto_id: product.id,
          nombre: name,
          cantidad: 1,
          precio_unitario: price,
          costo_unitario: cost,
          margen_porcentaje: bulkMarginPercent,
          unidad,
        },
      ],
    }));
  };

  const setLine = (index: number, patch: Partial<Linea>) => {
    setForm((current) => ({
      ...current,
      lineas: current.lineas.map((line, idx) => (idx === index ? { ...line, ...patch } : line)),
    }));
  };

  const setLineCost = (index: number, value: number) => {
    setForm((current) => ({
      ...current,
      lineas: current.lineas.map((line, idx) => {
        if (idx !== index) return line;
        const margin = lineMarginPercent(line);
        return {
          ...line,
          costo_unitario: value,
          margen_porcentaje: margin,
          precio_unitario: priceFromCostAndMargin(value, margin),
        };
      }),
    }));
  };

  const setLineMargin = (index: number, value: number) => {
    setForm((current) => ({
      ...current,
      lineas: current.lineas.map((line, idx) =>
        idx === index
          ? {
              ...line,
              margen_porcentaje: value,
              precio_unitario: priceFromCostAndMargin(line.costo_unitario || 0, value),
            }
          : line
      ),
    }));
  };

  const setAllLineMargins = (value: number) => {
    setBulkMarginPercent(value);
    setForm((current) => ({
      ...current,
      lineas: current.lineas.map((line) => ({
        ...line,
        margen_porcentaje: value,
        precio_unitario: priceFromCostAndMargin(line.costo_unitario || 0, value),
      })),
    }));
  };

  const setLinePrice = (index: number, value: number) => {
    setForm((current) => ({
      ...current,
      lineas: current.lineas.map((line, idx) =>
        idx === index
          ? {
              ...line,
              precio_unitario: value,
              margen_porcentaje: marginFromCostAndPrice(line.costo_unitario || 0, value),
            }
          : line
      ),
    }));
  };

  const removeLine = (index: number) => {
    setForm((current) => ({
      ...current,
      lineas: current.lineas.filter((_, idx) => idx !== index),
    }));
  };

  const saveCurrentClient = () => {
    setClientSaveStatus("");
    const clientCompany = form.cliente_empresa.trim();
    const contact = form.cliente_persona.trim();
    if (!clientCompany && !contact) {
      setClientSaveStatus("Captura Empresa o Atencion a: antes de guardar.");
      return;
    }
    const id = (clientCompany || contact).toLowerCase();
    const nextClient: SavedClient = {
      id,
      cliente_empresa: form.cliente_empresa,
      cliente_persona: form.cliente_persona,
      obra: form.obra,
      lugar_entrega: form.lugar_entrega,
      nota1: form.nota1,
      nota2: form.nota2,
      nota3: form.nota3,
      updated_at: new Date().toISOString(),
    };
    const next = [nextClient, ...savedClients.filter((client) => client.id !== id)].slice(0, 50);
    try {
      localStorage.setItem(clientStorageKey, JSON.stringify(next));
      setSavedClients(next);
      setClientSaveStatus("Cliente guardado.");
    } catch {
      setClientSaveStatus("No se pudo guardar en este navegador.");
    }
  };

  const saveQuoteCompany = () => {
    setQuoteCompanySaveStatus("");
    const value = form.empresa_cotiza.trim();
    if (!value) {
      setQuoteCompanySaveStatus("Captura la empresa.");
      return;
    }
    const id = value.toLowerCase();
    const nextCompany: SavedQuoteCompany = { id, empresa_cotiza: form.empresa_cotiza, updated_at: new Date().toISOString() };
    const next = [nextCompany, ...savedQuoteCompanies.filter((company) => company.id !== id)].slice(0, 30);
    try {
      localStorage.setItem(quoteCompanyStorageKey, JSON.stringify(next));
      setSavedQuoteCompanies(next);
      setQuoteCompanySaveStatus("Guardada.");
    } catch {
      setQuoteCompanySaveStatus("No se pudo guardar.");
    }
  };

  const applyQuoteCompany = (companyId: string) => {
    const company = savedQuoteCompanies.find((item) => item.id === companyId);
    if (!company) return;
    setForm((current) => ({ ...current, empresa_cotiza: company.empresa_cotiza }));
  };

  const applySavedClient = (clientId: string) => {
    const client = savedClients.find((item) => item.id === clientId);
    if (!client) return;
    setForm((current) => ({
      ...current,
      cliente_empresa: client.cliente_empresa,
      cliente_persona: client.cliente_persona,
      obra: client.obra,
      lugar_entrega: client.lugar_entrega,
      nota1: client.nota1,
      nota2: client.nota2,
      nota3: client.nota3,
    }));
  };

  if (!mounted || authLoading) return null;

  if (!auth.company_id) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-5">
        <section className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
            <ReceiptText size={22} />
          </span>
          <p className="mt-5 text-sm font-semibold uppercase tracking-[0.18em] text-blue-300">Apps4All module</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Coti4All</h1>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Entra con tu cuenta Apps4All para abrir el cotizador de tu empresa.
          </p>
          <Link
            href={portalHref}
            className="mt-5 inline-flex w-full items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600"
          >
            Ir a Apps4All
          </Link>
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          <Link href={portalHref} className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
              <Sparkles size={18} />
            </span>
            <div>
              <p className="text-sm font-bold text-white">Apps4All</p>
              <p className="text-xs text-slate-400">Coti4All / Cotizador</p>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-200">{String(auth.email || "")}</p>
              <p className="text-xs text-slate-500">{String(auth.company_name || selectedCompanyId || "Sin empresa")}</p>
            </div>
            <Link href="/settings" className="btn-ghost inline-flex h-9 w-9 items-center justify-center p-0" title="Settings">
              <Settings size={16} />
            </Link>
            <form action="/api/auth/logout" method="post">
              <button className="btn-ghost inline-flex h-9 w-9 items-center justify-center p-0" title="Salir">
                <LogOut size={16} />
              </button>
            </form>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-5 px-5 py-6">
        <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-300">Modulo activo</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Cotizaciones de venta</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Catalogo, precios, margen y documento imprimible conectados a Factory3 por grants Apps4All.
            </p>
          </div>
          <Link href={portalHref} className="btn-ghost inline-flex items-center justify-center gap-2 px-4 py-2">
            Apps4All <ChevronRight size={15} />
          </Link>
        </section>

        <section className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Empresa de trabajo</p>
              <p className="mt-1 text-sm text-slate-300">Es la empresa donde se guarda esta cotizacion (folio, cliente, totales).</p>
            </div>
            <select
              value={selectedCompanyId}
              onChange={(event) => setSelectedCompanyId(event.target.value)}
              className="min-h-10 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-white outline-none focus:border-blue-500"
            >
              {companies.map((company) => (
                <option key={company.company_id} value={company.company_id}>
                  {company.name || company.company_id}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-5">
          <Metric label="Folio" value={form.folio || "Sin guardar"} />
          <Metric label="Empresa" value={selectedCompany?.name || selectedCompanyId || "-"} />
          <Metric label="Lineas" value={String(form.lineas.length)} />
          <Metric label="Subtotal" value={currency.format(totals.subtotal)} />
          <Metric label="Catalogo" value={catalogo.length ? `${catalogo.length} items` : "Sin datos"} />
        </section>

        <ol className="flex flex-wrap items-center gap-2 text-sm">
          {["Cotizacion", "Revision", "Documento", "Cotizaciones"].map((label, idx) => (
            <li key={label} className="flex items-center gap-2">
              <button
                onClick={() => setStep((idx + 1) as 1 | 2 | 3 | 4)}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                  step === idx + 1
                    ? "border-blue-500 bg-blue-500 text-white"
                    : idx + 1 < step
                      ? "border-slate-600 bg-slate-800 text-slate-200"
                      : "border-slate-700 text-slate-400"
                }`}
              >
                {idx + 1}. {label}
              </button>
              {idx < 3 && <ChevronRight className="text-slate-600" size={14} />}
            </li>
          ))}
        </ol>

        {step === 1 && (
          <section className="grid gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div className="card space-y-4">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-[#e4ece6] text-moss">
                  <FileText size={19} />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-ink">Datos Cotizacion</h2>
                  <p className="text-sm text-slate-500">Datos que se mostraran en el documento</p>
                </div>
              </div>
              <div className="space-y-3">
                {savedClients.length ? (
                  <Field label="Elegir cliente guardado">
                    <select
                      className="input"
                      defaultValue=""
                      onChange={(event) => {
                        applySavedClient(event.target.value);
                        event.currentTarget.value = "";
                      }}
                    >
                      <option value="">Elegir cliente...</option>
                      {savedClients.map((client) => (
                        <option key={client.id} value={client.id}>
                          {client.cliente_empresa || client.cliente_persona}
                          {client.cliente_persona && client.cliente_empresa ? ` / ${client.cliente_persona}` : ""}
                        </option>
                      ))}
                    </select>
                  </Field>
                ) : (
                  <div className="rounded-md border border-dashed border-border bg-slate-50 px-3 py-2 text-sm text-slate-500">
                    Captura un cliente abajo y guardalo para que aparezca aqui.
                  </div>
                )}
                {savedQuoteCompanies.length ? (
                  <Field label="Elegir empresa que cotiza">
                    <select
                      className="input"
                      defaultValue=""
                      onChange={(event) => {
                        applyQuoteCompany(event.target.value);
                        event.currentTarget.value = "";
                      }}
                    >
                      <option value="">Elegir empresa...</option>
                      {savedQuoteCompanies.map((company) => (
                        <option key={company.id} value={company.id}>
                          {company.empresa_cotiza}
                        </option>
                      ))}
                    </select>
                  </Field>
                ) : null}
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2">
                  <Field label="Empresa que cotiza">
                    <input className="input" placeholder="Empresa que va en el encabezado" value={form.empresa_cotiza} onChange={(e) => setForm({ ...form, empresa_cotiza: e.target.value })} />
                  </Field>
                  <button type="button" onClick={saveQuoteCompany} className="rounded-md border border-border bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-700">
                    Guardar
                  </button>
                </div>
                {quoteCompanySaveStatus && <p className="text-xs font-medium text-slate-500">{quoteCompanySaveStatus}</p>}
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Empresa">
                    <input className="input" placeholder="Empresa cliente" value={form.cliente_empresa} onChange={(e) => setForm({ ...form, cliente_empresa: e.target.value })} />
                  </Field>
                  <Field label="Atencion a:">
                    <input className="input" placeholder="Persona contacto" value={form.cliente_persona} onChange={(e) => setForm({ ...form, cliente_persona: e.target.value })} />
                  </Field>
                </div>
                <Field label="Obra">
                  <input className="input" placeholder="Nombre o referencia de obra" value={form.obra} onChange={(e) => setForm({ ...form, obra: e.target.value })} />
                </Field>
                <Field label="Lugar de entrega">
                  <input className="input" placeholder="Direccion o zona de entrega" value={form.lugar_entrega} onChange={(e) => setForm({ ...form, lugar_entrega: e.target.value })} />
                </Field>
                <button type="button" onClick={saveCurrentClient} className="inline-flex w-fit items-center justify-center rounded-md border border-border bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-700">
                  Guardar cliente
                </button>
                {clientSaveStatus && <p className="text-xs font-medium text-slate-500">{clientSaveStatus}</p>}
                <div className="grid grid-cols-3 gap-2">
                  <Field label="Nota 1">
                    <input className="input" placeholder="Nota 1" value={form.nota1} onChange={(e) => setForm({ ...form, nota1: e.target.value })} />
                  </Field>
                  <Field label="Nota 2">
                    <input className="input" placeholder="Nota 2" value={form.nota2} onChange={(e) => setForm({ ...form, nota2: e.target.value })} />
                  </Field>
                  <Field label="Nota 3">
                    <input className="input" placeholder="Nota 3" value={form.nota3} onChange={(e) => setForm({ ...form, nota3: e.target.value })} />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Moneda">
                    <select className="input" value={form.moneda} onChange={(e) => setForm({ ...form, moneda: e.target.value })}>
                      <option>MXN</option>
                      <option>USD</option>
                      <option>EUR</option>
                    </select>
                  </Field>
                  <Field label="Validez">
                    <input type="number" className="input" value={form.validez_dias} onChange={(e) => setForm({ ...form, validez_dias: Number(e.target.value) })} />
                  </Field>
                </div>
                <button onClick={addManualLine} className="btn-primary inline-flex w-full items-center justify-center gap-2 px-4 py-2">
                  <PackagePlus size={16} /> Agregar renglon manual
                </button>
              </div>
            </div>

            <div className="card space-y-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-ink">Catalogo</h2>
                  <p className="text-sm text-slate-500">Items disponibles para la empresa</p>
                </div>
                <select
                  className="rounded-md border border-border bg-white px-2 py-2 text-sm font-semibold text-ink"
                  value={catalogCompanyId}
                  onChange={(event) => setCatalogCompanyId(event.target.value)}
                >
                  {companies.map((company) => (
                    <option key={company.company_id} value={company.company_id}>
                      Catalogo de: {company.name || company.company_id}
                    </option>
                  ))}
                </select>
              </div>
              <input
                className="input"
                placeholder="Buscar producto por nombre o SKU..."
                value={catalogSearch}
                onChange={(e) => {
                  setCatalogSearch(e.target.value);
                  setCatalogVisibleCount(30);
                }}
              />
              {(() => {
                const q = catalogSearch.trim().toLowerCase();
                const filtered = q
                  ? catalogo.filter((item) => {
                      const name = String(item.nombre || item.product_name || "").toLowerCase();
                      const code = String(item.sku || item.product_code || "").toLowerCase();
                      return name.includes(q) || code.includes(q);
                    })
                  : catalogo;
                const visible = filtered.slice(0, catalogVisibleCount);
                return (
                  <>
                    <p className="text-xs text-slate-500">
                      Mostrando {visible.length} de {filtered.length} productos
                      {q ? ` (filtrado de ${catalogo.length})` : ""}
                    </p>
                    <div className="max-h-[360px] space-y-2 overflow-auto pr-1">
                      {filtered.length === 0 && (
                        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                          {catalogo.length === 0 ? catalogStatus : "Sin productos que coincidan con la búsqueda."}
                        </div>
                      )}
                      {visible.map((item) => {
                        const name = item.nombre || item.product_name || "Producto";
                        const code = item.sku || item.product_code || "";
                        const cost = Number(item.costo ?? item.costo_referencia ?? 0);
                        const price = priceFromCostAndMargin(cost, bulkMarginPercent);
                        const addedCount = form.lineas.filter((line) => line.producto_id === item.id).length;
                        return (
                          <div key={item.id} className="flex items-center justify-between rounded-md border border-border bg-white px-3 py-2 text-sm">
                            <div>
                              <p className="font-medium text-ink">{name}</p>
                              <p className="text-xs text-slate-500">
                                {code || "Sin SKU"} {addedCount ? `· Agregado: ${addedCount}` : ""}
                              </p>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-medium text-ink">{price ? currency.format(price) : "-"}</span>
                              <button onClick={() => addProduct(item)} className="btn-primary inline-flex items-center gap-1 px-3 py-1.5 text-xs">
                                <PlusCircle size={14} /> Agregar
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {filtered.length > visible.length && (
                      <button
                        type="button"
                        onClick={() => setCatalogVisibleCount((n) => n + 30)}
                        className="btn-ghost w-full py-2 text-sm"
                      >
                        Mostrar más ({filtered.length - visible.length} restantes)
                      </button>
                    )}
                  </>
                );
              })()}
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="space-y-4">
            <div className="card">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <h2 className="text-lg font-semibold text-ink">Resumen</h2>
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <span className="font-medium">% margen general</span>
                  <input
                    type="number"
                    className="w-24 rounded border border-border bg-white px-2 py-1 text-sm text-ink"
                    value={bulkMarginPercent}
                    onChange={(e) => setAllLineMargins(Number(e.target.value))}
                  />
                </label>
              </div>
              <div className="mt-4 overflow-x-auto rounded-md border border-border">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left">Costo unitario</th>
                      <th className="px-3 py-2 text-right">Costo</th>
                      <th className="px-3 py-2">% margen</th>
                      <th className="px-3 py-2 text-right">Margen venta</th>
                      <th className="px-3 py-2 text-left">Nombre</th>
                      <th className="px-3 py-2">Cant</th>
                      <th className="px-3 py-2">Precio</th>
                      <th className="px-3 py-2 text-left">Unidad</th>
                      <th className="px-3 py-2 text-right">Importe</th>
                      <th className="px-3 py-2 text-right">Quitar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {form.lineas.length === 0 && (
                      <tr>
                        <td colSpan={10} className="px-3 py-8 text-center text-sm text-slate-500">
                          Agrega productos o renglones manuales para revisar la cotizacion.
                        </td>
                      </tr>
                    )}
                    {form.lineas.map((line, index) => {
                      const rowCosto = line.cantidad * (line.costo_unitario || 0);
                      const rowImporte = line.cantidad * line.precio_unitario;
                      const rowMargen = rowImporte - rowCosto;
                      const unidadIsPreset = UNIDAD_PRESETS.includes(line.unidad);
                      return (
                        <tr key={index}>
                          <td className="px-3 py-2">
                            <input type="number" className="w-28 rounded border border-border bg-white px-2 py-1 text-sm text-ink" value={line.costo_unitario} onChange={(e) => setLineCost(index, Number(e.target.value))} />
                          </td>
                          <td className="px-3 py-2 text-right text-ink">
                            {currency.format(rowCosto)}
                          </td>
                          <td className="px-3 py-2">
                            <input
                              type="number"
                              className="w-24 rounded border border-border bg-white px-2 py-1 text-sm text-ink"
                              value={lineMarginPercent(line)}
                              onChange={(e) => setLineMargin(index, Number(e.target.value))}
                            />
                          </td>
                          <td className="px-3 py-2 text-right text-ink">
                            {currency.format(rowMargen)}
                          </td>
                          <td className="px-3 py-2">
                            <input className="w-full rounded border border-border bg-white px-2 py-1 text-sm text-ink" value={line.nombre} onChange={(e) => setLine(index, { nombre: e.target.value })} />
                          </td>
                          <td className="px-3 py-2">
                            <input type="number" className="w-16 rounded border border-border bg-white px-2 py-1 text-sm text-ink" value={line.cantidad} onChange={(e) => setLine(index, { cantidad: Number(e.target.value) })} />
                          </td>
                          <td className="px-3 py-2">
                            <input type="number" className="w-28 rounded border border-border bg-white px-2 py-1 text-sm text-ink" value={line.precio_unitario} onChange={(e) => setLinePrice(index, Number(e.target.value))} />
                          </td>
                          <td className="px-3 py-2">
                            <select
                              className="w-24 rounded border border-border bg-white px-2 py-1 text-sm text-ink"
                              value={unidadIsPreset ? line.unidad : "OTRO"}
                              onChange={(e) => setLine(index, { unidad: e.target.value === "OTRO" ? "" : e.target.value })}
                            >
                              {UNIDAD_PRESETS.map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                              <option value="OTRO">Otro...</option>
                            </select>
                            {!unidadIsPreset && (
                              <input
                                className="mt-1 w-24 rounded border border-border bg-white px-2 py-1 text-sm text-ink"
                                placeholder="Unidad"
                                value={line.unidad}
                                onChange={(e) => setLine(index, { unidad: e.target.value })}
                              />
                            )}
                          </td>
                          <td className="px-3 py-2 text-right text-ink">
                            {currency.format(rowImporte)}
                          </td>
                          <td className="px-3 py-2 text-right">
                            <button
                              type="button"
                              onClick={() => removeLine(index)}
                              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-red-100 bg-red-50 text-red-600 hover:border-red-200 hover:bg-red-100"
                              title="Eliminar renglon"
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot className="bg-slate-50">
                    <tr className="border-t-2 border-slate-300 align-top">
                      <td className="px-3 py-2 text-xs font-semibold uppercase text-slate-500">Totales</td>
                      <td className="px-3 py-2 text-right">
                        <TotalStack subtotal={totals.costoSubtotal} iva={costoIva} total={costoTotal} ivaLabel="IVA (16%)" />
                      </td>
                      <td className="px-3 py-2" />
                      <td className="px-3 py-2 text-right">
                        <TotalStack subtotal={totals.margenSubtotal} iva={margenIva} total={margenTotal} ivaLabel="IVA (0%)" />
                      </td>
                      <td className="px-3 py-2" colSpan={4} />
                      <td className="px-3 py-2 text-right">
                        <TotalStack subtotal={totals.subtotal} iva={iva} total={total} ivaLabel="IVA (16%)" />
                      </td>
                      <td className="px-3 py-2" />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </section>
        )}

        {step === 3 && (
          <section className="card">
            <h2 className="text-lg font-semibold text-ink">Documento imprimible</h2>
            <PreviewPdf form={documentPayload} />
          </section>
        )}

        {step === 4 && (
          <section className="card">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-[#e4ece6] text-moss">
                  <ListOrdered size={19} />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-ink">Cotizaciones guardadas</h2>
                  <p className="text-sm text-slate-500">Cotizaciones de {selectedCompany?.name || selectedCompanyId || "la empresa"}</p>
                </div>
              </div>
              <button type="button" onClick={loadQuotes} className="btn-ghost px-3 py-2 text-xs">
                Actualizar
              </button>
            </div>
            <div className="mt-4 overflow-x-auto rounded-md border border-border">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Folio</th>
                    <th className="px-3 py-2 text-left">Cliente</th>
                    <th className="px-3 py-2 text-left">Estado</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-left">Fecha</th>
                    <th className="px-3 py-2 text-right">Editar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {quotesLoading && (
                    <tr>
                      <td colSpan={6} className="px-3 py-8 text-center text-sm text-slate-500">
                        Cargando cotizaciones...
                      </td>
                    </tr>
                  )}
                  {!quotesLoading && quotesError && (
                    <tr>
                      <td colSpan={6} className="px-3 py-8 text-center text-sm text-red-600">
                        {quotesError}
                      </td>
                    </tr>
                  )}
                  {!quotesLoading && !quotesError && quotes.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-3 py-8 text-center text-sm text-slate-500">
                        Todavia no hay cotizaciones guardadas para esta empresa.
                      </td>
                    </tr>
                  )}
                  {!quotesLoading &&
                    quotes.map((q) => (
                      <tr key={q.id}>
                        <td className="px-3 py-2 font-medium text-ink">{q.folio}</td>
                        <td className="px-3 py-2 text-ink">{q.client_nombre || "-"}</td>
                        <td className="px-3 py-2 text-slate-600">{q.status || "draft"}</td>
                        <td className="px-3 py-2 text-right text-ink">{currency.format(Number(q.total || 0))}</td>
                        <td className="px-3 py-2 text-slate-600">
                          {q.created_at ? new Date(q.created_at).toLocaleDateString("es-MX") : "-"}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => editQuote(q.id)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700"
                            title="Editar cotizacion"
                          >
                            <Pencil size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <div className="sticky bottom-4 flex flex-col gap-3 rounded-lg border border-slate-700 bg-slate-950/90 px-4 py-3 shadow-xl backdrop-blur md:flex-row md:items-center md:justify-between">
          <div className="text-sm text-slate-300">
            Cliente: <span className="font-medium text-white">{form.cliente_empresa || form.cliente_persona || "-"}</span> · Total estimado:{" "}
            {currency.format(total)}
            {form.folio && <span className="ml-2 text-slate-400">· Folio: {form.folio}</span>}
            {saveStatus && <span className="ml-2 text-slate-400">· {saveStatus}</span>}
          </div>
          <div className="flex items-center gap-2">
            {step > 1 && (
              <button onClick={() => setStep((current) => (current - 1) as 1 | 2 | 3 | 4)} className="btn-ghost px-3 py-2 text-sm">
                Anterior
              </button>
            )}
            {step < 4 && (
              <button
                type="button"
                disabled={savingQuote}
                onClick={saveQuote}
                className="btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm"
              >
                {savingQuote && <Loader2 className="animate-spin" size={14} />}
                Guardar cotizacion
              </button>
            )}
            {step < 4 && (
              <button onClick={() => setStep((current) => (current + 1) as 1 | 2 | 3 | 4)} className="btn-primary px-3 py-2 text-sm">
                Siguiente
              </button>
            )}
            {step === 3 && (
              <button
                disabled={loading}
                onClick={async () => {
                  setLoading(true);
                  try {
                    const res = await fetch("/api/cotizador/pdf", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify(documentPayload),
                    });
                    const json = await res.json();
                    if (!res.ok) throw new Error(json.error || "Error al generar documento");
                    if (!json.html) throw new Error("Documento no disponible para esta cotizacion");
                    const blob = new Blob([json.html], { type: "text/html;charset=utf-8" });
                    window.open(URL.createObjectURL(blob), "_blank");
                  } catch (error) {
                    alert((error as Error).message);
                  } finally {
                    setLoading(false);
                  }
                }}
                className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm"
              >
                {loading && <Loader2 className="animate-spin" size={16} />}
                {loading ? "Generando..." : "Guardar PDF"}
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function TotalStack({ subtotal, iva, total, ivaLabel }: { subtotal: number; iva: number; total: number; ivaLabel: string }) {
  return (
    <div className="space-y-0.5 text-xs text-slate-500">
      <p>Subtotal: {currency.format(subtotal)}</p>
      <p>
        {ivaLabel}: {currency.format(iva)}
      </p>
      <p className="text-sm font-semibold text-ink">Total: {currency.format(total)}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label>
      <span className="label">{label}</span>
      {children}
    </label>
  );
}


function PreviewPdf({ form }: { form: Cotizacion }) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState("Generando vista previa...");

  useEffect(() => {
    setStatus("Generando vista previa...");
    if (url) URL.revokeObjectURL(url);
    setUrl(null);
    fetch("/api/cotizador/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
      .then(async (res) => {
        if (!res.ok) {
          setStatus("No se pudo generar la vista previa.");
          return;
        }
        const json = await res.json();
        if (!json.html) {
          setStatus("Documento sin contenido disponible.");
          return;
        }
        const blob = new Blob([json.html], { type: "text/html;charset=utf-8" });
        setUrl(URL.createObjectURL(blob));
        setStatus("");
      })
      .catch(() => setStatus("No se pudo generar la vista previa."));
  }, [form]);

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">Vista previa del documento imprimible.</p>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
          Carta / desktop
        </span>
      </div>
      {url ? (
        <div className="overflow-auto rounded-lg border border-slate-200 bg-slate-200/70 p-6">
          <iframe
            src={url}
            className="mx-auto h-[760px] w-[816px] max-w-full rounded-sm border border-slate-300 bg-white shadow-2xl"
            title="Vista previa de cotizacion"
          />
        </div>
      ) : (
        <div className="flex h-[520px] items-center justify-center rounded-lg border border-dashed border-border bg-slate-50 text-sm text-slate-500">
          {status}
        </div>
      )}
    </div>
  );
}
