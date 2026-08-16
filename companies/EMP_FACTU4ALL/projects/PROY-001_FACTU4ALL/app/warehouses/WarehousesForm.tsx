"use client";

import { useEffect, useState } from "react";

type Warehouse = { id: string; code: string; name: string; is_default: boolean; status: string };

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

export default function WarehousesForm() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ code: "", name: "", is_default: false });

  async function refresh() {
    setLoading(true);
    const res = await api<{ warehouses: Warehouse[] }>("/api/factu4all/warehouses");
    setWarehouses(res.data?.warehouses || []);
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Guardando...");
    const res = await api("/api/factu4all/warehouses", { method: "POST", body: JSON.stringify(form) });
    setMessage(res.ok ? "Guardado." : `Error: ${res.error}`);
    if (res.ok) {
      setForm({ code: "", name: "", is_default: false });
      refresh();
    }
  }

  return (
    <div className="mt-6 space-y-6">
      {message && <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{message}</p>}

      <section className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Nuevo almacén</h2>
        <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="label">Código</span>
            <input className="input" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
          </label>
          <label className="block">
            <span className="label">Nombre</span>
            <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="flex items-end gap-2">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
            <span className="text-sm">Almacén por defecto</span>
          </label>
          <div className="sm:col-span-3">
            <button className="btn-primary px-4 py-2" type="submit">Guardar</button>
          </div>
        </form>
      </section>

      <section className="card">
        {loading ? (
          <p className="text-sm text-slate-500">Cargando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Código</th><th>Nombre</th><th>Por defecto</th><th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {warehouses.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-1">{row.code}</td>
                    <td>{row.name}</td>
                    <td>{row.is_default ? "Sí" : "No"}</td>
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
