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
  lot_cost_snapshot?: number | null;
  weighted_avg_cost_before?: number | null;
  weighted_avg_cost_after?: number | null;
  last_purchase_cost_snapshot?: number | null;
};

type Valuation = {
  product_id: string;
  fiscal_product_name?: string;
  source_product_key?: string;
  warehouse_code?: string;
  environment: string;
  year: number;
  month: number;
  closing_qty: number;
  closing_value: number;
};

async function api<T = any>(url: string): Promise<{ ok: boolean; data?: T; error?: string }> {
  const res = await fetch(url);
  return res.json().catch(() => ({ ok: false, error: "parse error" }));
}

export default function KardexTable() {
  const [movements, setMovements] = useState<Movement[]>([]);
  const [valuation, setValuation] = useState<Valuation[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [mvRes, valRes] = await Promise.all([
        api<{ movements: Movement[] }>("/api/factu4all/kardex"),
        api<{ valuation: Valuation[]; total_value: number }>("/api/factu4all/valuation"),
      ]);
      setMovements(mvRes.data?.movements || []);
      setValuation(valRes.data?.valuation || []);
      setTotalValue(valRes.data?.total_value || 0);
      setLoading(false);
    })();
  }, []);

  return (
    <div className="mt-6 space-y-6">
      <div className="card">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase text-slate-500">Valuación de inventario (PEPS)</h2>
          <p className="text-lg font-semibold text-ink">${totalValue.toLocaleString("es-MX", { minimumFractionDigits: 2 })}</p>
        </div>
        {loading ? (
          <p className="mt-2 text-sm text-slate-500">Cargando...</p>
        ) : valuation.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Sin movimientos valuados todavía.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Producto</th>
                  <th>Almacén</th>
                  <th>Ambiente</th>
                  <th>Período</th>
                  <th>Existencia</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {valuation.map((row) => (
                  <tr key={`${row.product_id}-${row.warehouse_code}-${row.environment}`} className="border-t border-slate-100">
                    <td className="py-1">
                      {row.fiscal_product_name || "—"}
                      <div className="text-xs text-slate-400">{row.source_product_key}</div>
                    </td>
                    <td>{row.warehouse_code || "—"}</td>
                    <td>{row.environment}</td>
                    <td>{row.month}/{row.year}</td>
                    <td>{row.closing_qty}</td>
                    <td>${row.closing_value.toLocaleString("es-MX", { minimumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Movimientos</h2>
        {loading ? (
          <p className="mt-2 text-sm text-slate-500">Cargando...</p>
        ) : movements.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Todavía no hay movimientos en el kardex.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-1">Fecha</th>
                  <th>Movimiento</th>
                  <th>Producto</th>
                  <th>Clave SAT</th>
                  <th>Cantidad</th>
                  <th>Total</th>
                  <th>Costo (lote / prom. antes / prom. después / último)</th>
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
                    <td className="text-xs text-slate-500">
                      {row.movement_direction === "out" && row.lot_cost_snapshot != null
                        ? `$${row.lot_cost_snapshot} / $${row.weighted_avg_cost_before} / $${row.weighted_avg_cost_after} / $${row.last_purchase_cost_snapshot}`
                        : "—"}
                    </td>
                    <td className="max-w-[140px] truncate text-xs text-slate-500">{row.uuid || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
