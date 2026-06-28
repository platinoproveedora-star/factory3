"use client";
import { useState, useEffect, useCallback } from "react";

interface Rfc {
  id: string;
  rfc: string;
  label: string;
  folio: string;
}

export default function RfcsPage() {
  const [rfcs, setRfcs] = useState<Rfc[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ rfc: "", label: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadRfcs = useCallback(async () => {
    setLoading(true);
    const res = await fetch("/api/rfcs");
    const data = await res.json();
    if (data.ok) setRfcs(data.data?.rfcs ?? []);
    setLoading(false);
  }, []);

  useEffect(() => { loadRfcs(); }, [loadRfcs]);

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
    setForm({ rfc: "", label: "" });
    setShowForm(false);
    loadRfcs();
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar este RFC?")) return;
    const res = await fetch(`/api/rfcs?id=${id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.ok) loadRfcs();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">Mis RFCs</h1>
          <p className="text-muted text-sm">Administra los RFCs que sincronizas con el SAT</p>
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
            <div key={r.id} className="card flex items-center justify-between">
              <div>
                <p className="font-mono font-semibold">{r.rfc}</p>
                {r.label && <p className="text-muted text-sm">{r.label}</p>}
                <p className="text-xs text-slate-600 mt-0.5">{r.folio}</p>
              </div>
              <button
                onClick={() => handleDelete(r.id)}
                className="text-red-400 hover:text-red-300 text-sm transition-colors"
              >
                Eliminar
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
