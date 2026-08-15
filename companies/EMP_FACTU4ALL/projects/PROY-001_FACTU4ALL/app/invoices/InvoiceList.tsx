"use client";

import { useEffect, useState } from "react";

type Invoice = {
  id: string;
  folio: string;
  cfdi_folio: string;
  party_legal_name_snapshot: string;
  party_rfc_snapshot: string;
  total: number;
  status: string;
  uuid: string | null;
  created_at: string;
};

async function api<T = any>(url: string, init?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

export default function InvoiceList() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyFolio, setBusyFolio] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  async function refresh() {
    setLoading(true);
    const res = await api<{ cfdi_documents: Invoice[] }>("/api/factu4all/invoices?direction=issued");
    setInvoices(res.data?.cfdi_documents || []);
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function stamp(folio: string) {
    setBusyFolio(folio);
    setMessage("");
    const res = await api("/api/factu4all/invoices/stamp", { method: "POST", body: JSON.stringify({ folio }) });
    if (!res.ok) setMessage(res.error || "Error al timbrar");
    setBusyFolio(null);
    refresh();
  }

  async function cancel(folio: string) {
    if (!confirm(`¿Cancelar la factura ${folio}? Esta accion no se puede deshacer.`)) return;
    setBusyFolio(folio);
    setMessage("");
    const res = await api(`/api/factu4all/invoices/${encodeURIComponent(folio)}`, { method: "POST", body: JSON.stringify({ action: "cancel" }) });
    if (!res.ok) setMessage(res.error || "Error al cancelar");
    setBusyFolio(null);
    refresh();
  }

  async function download(folio: string, fileType: "xml" | "pdf") {
    setBusyFolio(folio);
    setMessage("");
    const res = await api(`/api/factu4all/invoices/${encodeURIComponent(folio)}`, { method: "POST", body: JSON.stringify({ action: "download", file_type: fileType }) });
    setBusyFolio(null);
    if (!res.ok) {
      setMessage(res.error || `No hay ${fileType.toUpperCase()} disponible para esta factura`);
      return;
    }
    const url = (res.data as any)?.url;
    if (url) window.open(url, "_blank");
  }

  return (
    <div className="mt-6 card">
      {message && <p className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>}
      {loading ? (
        <p className="text-sm text-slate-500">Cargando...</p>
      ) : invoices.length === 0 ? (
        <p className="text-sm text-slate-500">Todavía no hay facturas.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500">
                <th className="py-1">Folio</th>
                <th>Cliente</th>
                <th>Total</th>
                <th>Estado</th>
                <th>UUID</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  <td className="py-2">{row.cfdi_folio || row.folio}</td>
                  <td>
                    {row.party_legal_name_snapshot}
                    <div className="text-xs text-slate-400">{row.party_rfc_snapshot}</div>
                  </td>
                  <td>${row.total}</td>
                  <td>{row.status}</td>
                  <td className="max-w-[160px] truncate text-xs text-slate-500">{row.uuid || "—"}</td>
                  <td className="space-x-2 whitespace-nowrap py-1 text-right">
                    {row.status === "draft" && (
                      <button className="btn-ghost px-3 py-1 text-xs" disabled={busyFolio === row.folio} onClick={() => stamp(row.folio)}>
                        Timbrar
                      </button>
                    )}
                    {(row.status === "stamped" || row.status === "simulated") && (
                      <>
                        <button className="btn-ghost px-3 py-1 text-xs" disabled={busyFolio === row.folio} onClick={() => download(row.folio, "xml")}>
                          XML
                        </button>
                        <button className="btn-ghost px-3 py-1 text-xs" disabled={busyFolio === row.folio} onClick={() => download(row.folio, "pdf")}>
                          PDF
                        </button>
                        <button className="btn-ghost px-3 py-1 text-xs text-red-600" disabled={busyFolio === row.folio} onClick={() => cancel(row.folio)}>
                          Cancelar
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
