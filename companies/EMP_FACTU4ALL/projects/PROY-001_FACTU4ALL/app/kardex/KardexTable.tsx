"use client";

import { useEffect, useState } from "react";

type Movement = {
  id: string;
  movement_direction: string;
  business_effect?: string;
  fiscal_product_name_snapshot?: string;
  sat_product_key_snapshot?: string;
  source_product_key?: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  tax_amount: number;
  total: number;
  uuid?: string | null;
  created_at: string;
};

async function api<T = any>(url: string): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url);
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

export default function KardexTable() {
  const [movements, setMovements] = useState<Movement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await api<{ movements: Movement[] }>("/api/factu4all/kardex");
      setMovements(res.data?.movements || []);
      setLoading(false);
    })();
  }, []);

  return (
    <div className="mt-6 card">
      {loading ? (
        <p className="text-sm text-slate-500">Cargando...</p>
      ) : movements.length === 0 ? (
        <p className="text-sm text-slate-500">Todavía no hay movimientos en el kardex.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500">
                <th className="py-1">Fecha</th>
                <th>Movimiento</th>
                <th>Producto</th>
                <th>Clave SAT</th>
                <th>Cantidad</th>
                <th>Total</th>
                <th>UUID</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  <td className="py-2 text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</td>
                  <td>
                    <span className={row.movement_direction?.startsWith("out") ? "text-red-600" : "text-emerald-600"}>
                      {row.movement_direction}
                    </span>
                  </td>
                  <td>
                    {row.fiscal_product_name_snapshot || "—"}
                    <div className="text-xs text-slate-400">{row.source_product_key}</div>
                  </td>
                  <td>{row.sat_product_key_snapshot || "—"}</td>
                  <td>{row.quantity}</td>
                  <td>${row.total}</td>
                  <td className="max-w-[140px] truncate text-xs text-slate-500">{row.uuid || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
