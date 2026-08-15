"use client";

import { useEffect, useState } from "react";

type IssuerProfile = {
  id: string;
  rfc: string;
  legal_name: string;
  fiscal_regime?: string;
  expedition_place?: string;
  commercial_name?: string;
  fiscal_email?: string;
  fiscal_address?: string;
  status: string;
  csd_status: string;
  environment: string;
};

type FolioSeries = {
  id: string;
  series: string;
  cfdi_type: string;
  environment: string;
  is_default: boolean;
  next_number: number;
  status: string;
};

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function SettingsForm() {
  const [issuers, setIssuers] = useState<IssuerProfile[]>([]);
  const [series, setSeries] = useState<FolioSeries[]>([]);
  const [pacConfigured, setPacConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [issuerForm, setIssuerForm] = useState({
    rfc: "", legal_name: "", fiscal_regime: "", expedition_place: "",
    commercial_name: "", fiscal_email: "", fiscal_address: "", status: "ready",
  });
  const [companySettingsForm, setCompanySettingsForm] = useState({ country: "MX", default_pac_provider: "facturama", default_environment: "sandbox" });
  const [pacForm, setPacForm] = useState({ user: "", password: "", url: "https://apisandbox.facturama.mx" });
  const [csdForm, setCsdForm] = useState({ rfc: "", cer_b64: "", key_b64: "", password: "" });
  const [csdFileNames, setCsdFileNames] = useState({ cer: "", key: "" });
  const [seriesForm, setSeriesForm] = useState({ series: "F", cfdi_type: "ingreso", is_default: true });

  async function refresh() {
    setLoading(true);
    const [issuerRes, seriesRes, pacRes, settingsRes] = await Promise.all([
      api<{ issuer_profiles: IssuerProfile[] }>("/api/factu4all/issuer"),
      api<{ folio_series: FolioSeries[] }>("/api/factu4all/series"),
      api<{ configured: boolean }>("/api/factu4all/secrets/pac?pac_provider=facturama"),
      api<{ settings: any }>("/api/factu4all/company-settings"),
    ]);
    setIssuers(issuerRes.data?.issuer_profiles || []);
    setSeries(seriesRes.data?.folio_series || []);
    setPacConfigured(Boolean(pacRes.data?.configured));
    if (settingsRes.data?.settings) {
      const s = settingsRes.data.settings;
      setCompanySettingsForm({ country: s.country || "MX", default_pac_provider: s.default_pac_provider || "facturama", default_environment: s.default_environment || "sandbox" });
    }
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submitCompanySettings(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando configuracion...");
    const res = await api("/api/factu4all/company-settings", { method: "POST", body: JSON.stringify(companySettingsForm) });
    setMessage(res.ok ? "Configuracion guardada." : `Error: ${res.error}`);
    if (res.ok) refresh();
  }

  async function submitIssuer(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando emisor...");
    const res = await api("/api/factu4all/issuer", { method: "POST", body: JSON.stringify(issuerForm) });
    setMessage(res.ok ? "Emisor guardado." : `Error: ${res.error}`);
    if (res.ok) refresh();
  }

  async function submitPac(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando credenciales PAC...");
    const res = await api("/api/factu4all/secrets/pac", { method: "POST", body: JSON.stringify({ pac_provider: "facturama", ...pacForm }) });
    setMessage(res.ok ? "Credenciales PAC guardadas." : `Error: ${res.error}`);
    if (res.ok) {
      setPacForm({ user: "", password: "", url: pacForm.url });
      refresh();
    }
  }

  async function handleCsdFile(kind: "cer" | "key", file: File | null) {
    if (!file) return;
    const b64 = await readFileAsBase64(file);
    setCsdForm((prev) => ({ ...prev, [`${kind}_b64`]: b64 }));
    setCsdFileNames((prev) => ({ ...prev, [kind]: file.name }));
  }

  async function submitCsd(event: React.FormEvent) {
    event.preventDefault();
    if (!csdForm.cer_b64 || !csdForm.key_b64) {
      setMessage("Sube el archivo .cer y el archivo .key.");
      return;
    }
    setMessage("Guardando CSD...");
    const res = await api("/api/factu4all/secrets/csd", { method: "POST", body: JSON.stringify(csdForm) });
    setMessage(res.ok ? "CSD guardado." : `Error: ${res.error}`);
    if (res.ok) {
      setCsdForm({ rfc: csdForm.rfc, cer_b64: "", key_b64: "", password: "" });
      setCsdFileNames({ cer: "", key: "" });
      refresh();
    }
  }

  async function submitSeries(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando serie...");
    const res = await api("/api/factu4all/series", { method: "POST", body: JSON.stringify(seriesForm) });
    setMessage(res.ok ? "Serie guardada." : `Error: ${res.error}`);
    if (res.ok) refresh();
  }

  const readyIssuer = issuers.some((row) => row.status === "ready");
  const hasDefaultSeries = series.some((row) => row.is_default);

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Listo para timbrar Sandbox</h2>
        <ul className="mt-2 space-y-1 text-sm">
          <li>{readyIssuer ? "✅" : "⬜"} Emisor fiscal completo</li>
          <li>{pacConfigured ? "✅" : "⬜"} Credenciales PAC configuradas</li>
          <li>{hasDefaultSeries ? "✅" : "⬜"} Serie default activa</li>
        </ul>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Configuración general</h2>
        <form onSubmit={submitCompanySettings} className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="label">País</span>
            <input className="input" value={companySettingsForm.country} onChange={(e) => setCompanySettingsForm({ ...companySettingsForm, country: e.target.value.toUpperCase() })} />
          </label>
          <label className="block">
            <span className="label">PAC por defecto</span>
            <input className="input" value={companySettingsForm.default_pac_provider} onChange={(e) => setCompanySettingsForm({ ...companySettingsForm, default_pac_provider: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Ambiente por defecto</span>
            <select className="input" value={companySettingsForm.default_environment} onChange={(e) => setCompanySettingsForm({ ...companySettingsForm, default_environment: e.target.value })}>
              <option value="sandbox">Sandbox</option>
              <option value="production">Producción</option>
            </select>
          </label>
          <div className="sm:col-span-3">
            <button className="btn-primary px-4 py-2" type="submit">Guardar configuración</button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Emisor fiscal</h2>
        <form onSubmit={submitIssuer} className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">RFC</span>
            <input className="input" required value={issuerForm.rfc} onChange={(e) => setIssuerForm({ ...issuerForm, rfc: e.target.value.toUpperCase() })} />
          </label>
          <label className="block">
            <span className="label">Razón social</span>
            <input className="input" required value={issuerForm.legal_name} onChange={(e) => setIssuerForm({ ...issuerForm, legal_name: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Régimen fiscal (clave SAT)</span>
            <input className="input" value={issuerForm.fiscal_regime} onChange={(e) => setIssuerForm({ ...issuerForm, fiscal_regime: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Código postal de expedición</span>
            <input className="input" value={issuerForm.expedition_place} onChange={(e) => setIssuerForm({ ...issuerForm, expedition_place: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Nombre comercial</span>
            <input className="input" value={issuerForm.commercial_name} onChange={(e) => setIssuerForm({ ...issuerForm, commercial_name: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Correo fiscal</span>
            <input className="input" type="email" value={issuerForm.fiscal_email} onChange={(e) => setIssuerForm({ ...issuerForm, fiscal_email: e.target.value })} />
          </label>
          <label className="block sm:col-span-2">
            <span className="label">Dirección fiscal</span>
            <input className="input" value={issuerForm.fiscal_address} onChange={(e) => setIssuerForm({ ...issuerForm, fiscal_address: e.target.value })} />
          </label>
          <div className="sm:col-span-2">
            <button className="btn-primary px-4 py-2" type="submit">Guardar emisor</button>
          </div>
        </form>

        {issuers.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">RFC</th><th>Razón social</th><th>Estado</th><th>CSD</th>
                </tr>
              </thead>
              <tbody>
                {issuers.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.rfc}</td>
                    <td>{row.legal_name}</td>
                    <td>{row.status}</td>
                    <td>{row.csd_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">
          Credenciales PAC (Facturama Sandbox) — {pacConfigured ? "configuradas" : "sin configurar"}
        </h2>
        <form onSubmit={submitPac} className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="label">Usuario</span>
            <input className="input" required value={pacForm.user} onChange={(e) => setPacForm({ ...pacForm, user: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Password</span>
            <input className="input" type="password" required value={pacForm.password} onChange={(e) => setPacForm({ ...pacForm, password: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">URL</span>
            <input className="input" required value={pacForm.url} onChange={(e) => setPacForm({ ...pacForm, url: e.target.value })} />
          </label>
          <div className="sm:col-span-3">
            <button className="btn-primary px-4 py-2" type="submit">Guardar credenciales PAC</button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">CSD Sandbox</h2>
        <form onSubmit={submitCsd} className="mt-3 grid gap-3">
          <label className="block">
            <span className="label">RFC del emisor</span>
            <input className="input" required value={csdForm.rfc} onChange={(e) => setCsdForm({ ...csdForm, rfc: e.target.value.toUpperCase() })} />
          </label>
          <label className="block">
            <span className="label">Certificado (.cer)</span>
            <input
              className="input"
              type="file"
              accept=".cer"
              onChange={(e) => handleCsdFile("cer", e.target.files?.[0] || null)}
            />
            {csdFileNames.cer && <p className="mt-1 text-xs text-slate-500">{csdFileNames.cer}</p>}
          </label>
          <label className="block">
            <span className="label">Llave (.key)</span>
            <input
              className="input"
              type="file"
              accept=".key"
              onChange={(e) => handleCsdFile("key", e.target.files?.[0] || null)}
            />
            {csdFileNames.key && <p className="mt-1 text-xs text-slate-500">{csdFileNames.key}</p>}
          </label>
          <label className="block">
            <span className="label">Password de la llave</span>
            <input className="input" type="password" required value={csdForm.password} onChange={(e) => setCsdForm({ ...csdForm, password: e.target.value })} />
          </label>
          <div>
            <button className="btn-primary px-4 py-2" type="submit">Guardar CSD</button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Series de folios</h2>
        <form onSubmit={submitSeries} className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="label">Serie</span>
            <input className="input" required value={seriesForm.series} onChange={(e) => setSeriesForm({ ...seriesForm, series: e.target.value.toUpperCase() })} />
          </label>
          <label className="block">
            <span className="label">Tipo CFDI</span>
            <select className="input" value={seriesForm.cfdi_type} onChange={(e) => setSeriesForm({ ...seriesForm, cfdi_type: e.target.value })}>
              <option value="ingreso">Ingreso</option>
              <option value="egreso">Egreso</option>
            </select>
          </label>
          <label className="flex items-end gap-2">
            <input type="checkbox" checked={seriesForm.is_default} onChange={(e) => setSeriesForm({ ...seriesForm, is_default: e.target.checked })} />
            <span className="text-sm">Serie default</span>
          </label>
          <div className="sm:col-span-3">
            <button className="btn-primary px-4 py-2" type="submit">Guardar serie</button>
          </div>
        </form>

        {series.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Serie</th><th>Tipo</th><th>Siguiente folio</th><th>Default</th>
                </tr>
              </thead>
              <tbody>
                {series.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.series}</td>
                    <td>{row.cfdi_type}</td>
                    <td>{row.series}{String(row.next_number).padStart(4, "0")}</td>
                    <td>{row.is_default ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {loading && <p className="text-xs text-slate-400">Cargando...</p>}
    </div>
  );
}
