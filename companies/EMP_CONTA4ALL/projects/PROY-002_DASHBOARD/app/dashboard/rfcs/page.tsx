"use client";
import { useState, useEffect, useCallback } from "react";

const MODULE_CODE = "conta4all";

interface Rfc {
  id: string;
  rfc: string;
  label: string;
  folio: string;
  company_id?: string | null;
}

type CompanyOption = {
  company_id: string;
  name?: string;
};

export default function RfcsPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ rfc: "", label: "", company_id: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [assigningId, setAssigningId] = useState("");

  const loadRfcs = useCallback(async () => {
    setLoading(true);
    const res = await fetch("/api/rfcs");
    const data = await res.json();
    if (data.ok) setRfcs(data.data?.rfcs ?? []);
    setLoading(false);
  }, []);

  useEffect(() => { loadRfcs(); }, [loadRfcs]);

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
        setCompanies(rows);
      })
      .catch(() => {});
  }, []);

  function companyName(companyId?: string | null) {
    if (!companyId) return "Sin empresa asignada";
    return companies.find((c) => c.company_id === companyId)?.name || companyId;
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSuccess("");
    setSaving(true);
    const res = await fetch("/api/rfcs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const data = await res.json();
    setSaving(false);
    if (!data.ok) { setError(data.error || "Error al agregar RFC"); return; }
    setSuccess("RFC agregado correctamente");
    setForm({ rfc: "", label: "", company_id: "" });
    setShowForm(false);
    loadRfcs();
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar este RFC?")) return;
    const res = await fetch(`/api/rfcs?id=${id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.ok) loadRfcs();
  }

  async function handleAssignCompany(id: string, companyId: string) {
    setAssigningId(id);
    try {
      const res = await fetch("/api/rfcs", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ managed_rfc_id: id, company_id: companyId || null }),
      });
      const data = await res.json();
      if (data.ok) loadRfcs();
    } finally {
      setAssigningId("");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">Mis RFCs</h1>
          <p className="text-muted text-sm">Administra los RFCs que sincronizas con el SAT y a que empresa pertenecen</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "+ Agregar RFC"}
        </button>
      </div>

      {success && (
        <p className="text-green-400 text-sm bg-green-900/20 border border-green-800 rounded-lg px-3 py-2 mb-4">
          {success}
        </p>
      )}

      {showForm && (
        <div className="card mb-6">
          <h2 className="font-semibold mb-4">Nuevo RFC</h2>
          <form onSubmit={handleAdd} className="space-y-4">
            <div>
              <label className="label">RFC</label>
              <input
                type="text"
                className="input font-mono uppercase"
                placeholder="XAXX010101000"
                value={form.rfc}
                onChange={(e) => setForm((f) => ({ ...f, rfc: e.target.value.toUpperCase() }))}
                required
                maxLength={13}
              />
            </div>
            <div>
              <label className="label">Etiqueta (opcional)</label>
              <input
                type="text"
                className="input"
                placeholder="Ej. Mi empresa principal"
                value={form.label}
                onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              />
            </div>
            {companies.length > 0 && (
              <div>
                <label className="label">Empresa (Apps4All)</label>
                <select
                  className="input"
                  value={form.company_id}
                  onChange={(e) => setForm((f) => ({ ...f, company_id: e.target.value }))}
                >
                  <option value="">Sin asignar</option>
                  {companies.map((company) => (
                    <option key={company.company_id} value={company.company_id}>
                      {company.name || company.company_id}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {error && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Guardando..." : "Agregar"}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-muted text-sm">Cargando...</p>
      ) : rfcs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-muted">No tienes RFCs registrados aún</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rfcs.map((r) => (
            <div key={r.id} className="card flex items-center justify-between gap-3">
              <div>
                <p className="font-mono font-semibold">{r.rfc}</p>
                {r.label && <p className="text-muted text-sm">{r.label}</p>}
                <p className="text-xs text-slate-600 mt-0.5">{r.folio}</p>
              </div>
              <div className="flex items-center gap-3">
                {companies.length > 0 ? (
                  <select
                    className="input py-1 text-xs"
                    value={r.company_id || ""}
                    disabled={assigningId === r.id}
                    onChange={(e) => handleAssignCompany(r.id, e.target.value)}
                  >
                    <option value="">Sin asignar</option>
                    {companies.map((company) => (
                      <option key={company.company_id} value={company.company_id}>
                        {company.name || company.company_id}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-muted text-xs">{companyName(r.company_id)}</span>
                )}
                <button
                  onClick={() => handleDelete(r.id)}
                  className="text-red-400 hover:text-red-300 text-sm transition-colors"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
