"use client";

import { useEffect, useState } from "react";

type Party = {
  id: string;
  rfc: string;
  legal_name: string;
  party_type: string;
  tax_regime?: string;
  tax_zip_code?: string;
  cfdi_use_default?: string;
  billing_email?: string;
  status: string;
};

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

const empty = { rfc: "", legal_name: "", tax_regime: "", tax_zip_code: "", cfdi_use_default: "G03", billing_email: "" };

export default function PartiesForm() {
  const [partyType, setPartyType] = useState<"customer" | "supplier">("customer");
  const [parties, setParties] = useState<Party[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState(empty);

  async function refresh(type: "customer" | "supplier") {
    setLoading(true);
    const res = await api<{ parties: Party[] }>(`/api/factu4all/parties?party_type=${type}`);
    setParties(res.data?.parties || []);
    setLoading(false);
  }

  useEffect(() => {
    refresh(partyType);
  }, [partyType]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando...");
    const res = await api("/api/factu4all/parties", { method: "POST", body: JSON.stringify({ ...form, rfc: form.rfc.toUpperCase(), party_type: partyType }) });
    setMessage(res.ok ? "Guardado." : `Error: ${res.error}`);
    if (res.ok) {
      setForm(empty);
      refresh(partyType);
    }
  }

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <div className="flex gap-2">
        <button
          className={partyType === "customer" ? "btn-primary px-4 py-2" : "btn-ghost px-4 py-2"}
          onClick={() => setPartyType("customer")}
        >
          Clientes
        </button>
        <button
          className={partyType === "supplier" ? "btn-primary px-4 py-2" : "btn-ghost px-4 py-2"}
          onClick={() => setPartyType("supplier")}
        >
          Proveedores
        </button>
      </div>

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">
          Nuevo {partyType === "customer" ? "cliente" : "proveedor"} fiscal
        </h2>
        <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">RFC</span>
            <input className="input" required value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Razón social</span>
            <input className="input" required value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Régimen fiscal (clave SAT)</span>
            <input className="input" value={form.tax_regime} onChange={(e) => setForm({ ...form, tax_regime: e.target.value })} />
          </label>
          <label className="block">
            <span className="label">Código postal</span>
            <input className="input" value={form.tax_zip_code} onChange={(e) => setForm({ ...form, tax_zip_code: e.target.value })} />
          </label>
          {partyType === "customer" && (
            <label className="block">
              <span className="label">Uso CFDI</span>
              <input className="input" value={form.cfdi_use_default} onChange={(e) => setForm({ ...form, cfdi_use_default: e.target.value.toUpperCase() })} />
            </label>
          )}
          <label className="block">
            <span className="label">Correo</span>
            <input className="input" type="email" value={form.billing_email} onChange={(e) => setForm({ ...form, billing_email: e.target.value })} />
          </label>
          <div className="sm:col-span-2">
            <button className="btn-primary px-4 py-2" type="submit">Guardar</button>
          </div>
        </form>
      </section>

      <section className="card">
        {loading ? (
          <p className="text-sm text-slate-500">Cargando...</p>
        ) : parties.length === 0 ? (
          <p className="text-sm text-slate-500">Todavía no hay {partyType === "customer" ? "clientes" : "proveedores"} fiscales.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">RFC</th><th>Razón social</th><th>Régimen</th><th>CP</th><th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {parties.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.rfc}</td>
                    <td>{row.legal_name}</td>
                    <td>{row.tax_regime || "—"}</td>
                    <td>{row.tax_zip_code || "—"}</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
