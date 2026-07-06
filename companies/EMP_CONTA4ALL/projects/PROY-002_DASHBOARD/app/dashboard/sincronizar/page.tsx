"use client";
import { useState, useEffect, useRef } from "react";
import { COMPANY_CHANGE_EVENT, COMPANY_STORAGE_KEY, RFC_STORAGE_KEY } from "@/components/nav";

const MODULE_CODE = "conta4all";

interface Rfc { id: string; rfc: string; label?: string; company_id?: string | null; }
interface CompanyOption { company_id: string; name?: string; }

type SyncState = "idle" | "starting" | "polling" | "finalizing" | "done" | "error";

function toB64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const reader = new FileReader();
    reader.onload = () => res((reader.result as string).split(",")[1]);
    reader.onerror = rej;
    reader.readAsDataURL(file);
  });
}

export default function SincronizarPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [form, setForm] = useState({
    managed_rfc_id: "",
    rfc: "",
    fecha_inicio: "",
    fecha_fin: "",
    tipo: "E",
    key_password: "",
  });
  const [cerFile, setCerFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const pollData = useRef<{ id_solicitud: string; cer_b64: string; key_b64: string }>({ id_solicitud: "", cer_b64: "", key_b64: "" });
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetch("/api/auth/grants/me")
      .then((res) => res.json())
      .then((json) => {
        const grants = Array.isArray(json.grants) ? json.grants : [];
        const allowedCompanyIds = new Set(
          grants
            .filter((grant: any) => grant.modulo_code === MODULE_CODE)
            .map((grant: any) => String(grant.company_id || ""))
            .filter(Boolean)
        );
        const rows = (Array.isArray(json.companies) ? json.companies : []).filter((company: CompanyOption) =>
          allowedCompanyIds.has(company.company_id)
        );
        const stored = window.localStorage.getItem(COMPANY_STORAGE_KEY) || "";
        const initialCompany =
          rows.find((company: CompanyOption) => company.company_id === stored)?.company_id ||
          rows.find((company: CompanyOption) => company.company_id === json.user?.company_id)?.company_id ||
          rows[0]?.company_id ||
          "";
        setCompanies(rows);
        setSelectedCompanyId(initialCompany);
      })
      .catch(() => {});

    const onCompanyChange = (event: Event) => {
      setSelectedCompanyId(String((event as CustomEvent).detail || ""));
    };
    window.addEventListener(COMPANY_CHANGE_EVENT, onCompanyChange);
    return () => {
      window.removeEventListener(COMPANY_CHANGE_EVENT, onCompanyChange);
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!selectedCompanyId) {
      setRfcs([]);
      setForm((f) => ({ ...f, managed_rfc_id: "", rfc: "" }));
      return;
    }
    window.localStorage.setItem(COMPANY_STORAGE_KEY, selectedCompanyId);
    window.dispatchEvent(new CustomEvent(COMPANY_CHANGE_EVENT, { detail: selectedCompanyId }));
    fetch(`/api/rfcs?company_id=${encodeURIComponent(selectedCompanyId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) {
          setRfcs([]);
          setForm((f) => ({ ...f, managed_rfc_id: "", rfc: "" }));
          return;
        }
        const rows = (d.data?.rfcs ?? []) as Rfc[];
        const storedRfc = window.localStorage.getItem(RFC_STORAGE_KEY) || "";
        const nextRfc = rows.find((r) => r.id === storedRfc) || rows[0];
        setRfcs(rows);
        setForm((f) => ({ ...f, managed_rfc_id: nextRfc?.id || "", rfc: nextRfc?.rfc || "" }));
      })
      .catch(() => setRfcs([]));
  }, [selectedCompanyId]);

  function selectRfc(id: string) {
    const r = rfcs.find((x) => x.id === id);
    if (id) window.localStorage.setItem(RFC_STORAGE_KEY, id);
    setForm((f) => ({ ...f, managed_rfc_id: id, rfc: r?.rfc ?? "" }));
  }

  function companyName(companyId?: string | null) {
    if (!companyId) return "Selecciona una empresa";
    return companies.find((c) => c.company_id === companyId)?.name || companyId;
  }

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    if (!cerFile || !keyFile) { setError("Sube los archivos .cer y .key"); return; }
    setError(""); setResult(null);
    setSyncState("starting");
    setStatus("Iniciando solicitud al SAT...");

    const cer_b64 = await toB64(cerFile);
    const key_b64 = await toB64(keyFile);

    const res = await fetch("/api/sync/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, cer_b64, key_b64 }),
    });
    const data = await res.json();
    if (!data.ok) {
      setError(data.error || "Error al iniciar"); setSyncState("error"); return;
    }
    const id_solicitud = data.data?.id_solicitud;
    pollData.current = { id_solicitud, cer_b64, key_b64 };
    setSyncState("polling");
    setStatus(`Solicitud creada: ${id_solicitud}. Verificando...`);
    schedulePoll();
  }

  function schedulePoll() {
    pollTimer.current = setTimeout(doPoll, 15000);
  }

  async function doPoll() {
    const { id_solicitud, cer_b64, key_b64 } = pollData.current;
    const res = await fetch("/api/sync/poll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, id_solicitud, cer_b64, key_b64 }),
    });
    const data = await res.json();
    if (!data.ok) {
      setError(data.error || "Error verificando"); setSyncState("error"); return;
    }
    const d = data.data ?? {};
    setStatus(`Estado: ${d.estado ?? "—"} · Paquetes: ${d.paquetes?.length ?? 0}`);
    if (d.vacio) {
      setStatus("El SAT no encontró CFDIs en ese período");
      setSyncState("done");
      setResult({ vacio: true });
      return;
    }
    if (!d.listo) { schedulePoll(); return; }
    setSyncState("finalizing");
    setStatus("Descargando y guardando CFDIs...");
    await doFinalize(d.id_solicitud, d.paquetes ?? [], cer_b64, key_b64);
  }

  async function doFinalize(id_solicitud: string, paquetes: string[], cer_b64: string, key_b64: string) {
    const res = await fetch("/api/sync/finalize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, id_solicitud, paquetes, cer_b64, key_b64 }),
    });
    const data = await res.json();
    if (!data.ok) {
      setError(data.error || "Error finalizando"); setSyncState("error"); return;
    }
    setSyncState("done");
    setStatus("Sincronización completada");
    setResult(data.data ?? {});
  }

  const isBusy = ["starting", "polling", "finalizing"].includes(syncState);

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-bold mb-1">Sincronizar SAT</h1>
      <p className="text-muted text-sm mb-6">Descarga tus CFDIs directamente del SAT</p>

      <div className="card mb-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Empresa activa</p>
            <p className="mt-1 text-sm text-slate-300">
              {companyName(selectedCompanyId)} - La descarga se guardara en el RFC de esta empresa.
            </p>
          </div>
          <select
            className="input md:max-w-sm"
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            disabled={!companies.length || isBusy}
          >
            {companies.length === 0 ? <option value="">Sin empresas disponibles</option> : null}
            {companies.map((company) => (
              <option key={company.company_id} value={company.company_id}>
                {company.name || company.company_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleStart} className="space-y-4">
          <div>
            <label className="label">RFC</label>
            <select
              className="input"
              value={form.managed_rfc_id}
              onChange={(e) => selectRfc(e.target.value)}
              required
              disabled={!selectedCompanyId}
            >
              <option value="">Selecciona un RFC</option>
              {rfcs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.rfc}{r.label ? ` — ${r.label}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Fecha inicio</label>
              <input type="date" className="input" value={form.fecha_inicio} onChange={(e) => setForm((f) => ({ ...f, fecha_inicio: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Fecha fin</label>
              <input type="date" className="input" value={form.fecha_fin} onChange={(e) => setForm((f) => ({ ...f, fecha_fin: e.target.value }))} required />
            </div>
          </div>

          <div>
            <label className="label">Tipo</label>
            <select className="input" value={form.tipo} onChange={(e) => setForm((f) => ({ ...f, tipo: e.target.value }))}>
              <option value="E">Ingresos (Emitidos)</option>
              <option value="R">Egresos (Recibidos)</option>
            </select>
          </div>

          <hr className="border-border" />
          <p className="text-sm text-muted">e.firma — solo se usa durante esta sesión</p>

          <div>
            <label className="label">Certificado (.cer)</label>
            <input type="file" accept=".cer" className="input py-1.5 text-sm" onChange={(e) => setCerFile(e.target.files?.[0] ?? null)} required />
          </div>
          <div>
            <label className="label">Llave privada (.key)</label>
            <input type="file" accept=".key" className="input py-1.5 text-sm" onChange={(e) => setKeyFile(e.target.files?.[0] ?? null)} required />
          </div>
          <div>
            <label className="label">Contraseña de la llave</label>
            <input type="password" className="input" placeholder="••••••••" value={form.key_password} onChange={(e) => setForm((f) => ({ ...f, key_password: e.target.value }))} required />
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {isBusy && (
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg px-3 py-2">
              <p className="text-blue-300 text-sm">{status}</p>
              <p className="text-blue-400 text-xs mt-1">Puede tomar varios minutos...</p>
            </div>
          )}

          {syncState === "done" && result && (
            <div className="bg-green-900/20 border border-green-800 rounded-lg px-3 py-2">
              <p className="text-green-400 text-sm font-medium">{status}</p>
              {!result.vacio && (
                <p className="text-green-300 text-xs mt-1">
                  {(result as { cfdis_guardados?: number }).cfdis_guardados ?? 0} CFDIs guardados
                  {" · "}{(result as { paquetes_procesados?: number }).paquetes_procesados ?? 0} paquetes
                </p>
              )}
              {((result as { log?: Array<{paso: string; ok: boolean; msg?: string}> }).log ?? []).map((l, i) => (
                <p key={i} className={`text-xs mt-0.5 ${l.ok ? "text-slate-400" : "text-red-400"}`}>
                  {l.ok ? "✓" : "✗"} {l.paso}{l.msg ? `: ${l.msg}` : ""}
                </p>
              ))}
              <pre className="text-xs text-slate-500 mt-2 overflow-auto max-h-40 bg-slate-900 rounded p-2">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          <button type="submit" className="btn-primary w-full" disabled={isBusy || !selectedCompanyId || !form.managed_rfc_id}>
            {isBusy ? "Sincronizando..." : "Iniciar sincronización"}
          </button>
        </form>
      </div>
    </div>
  );
}
