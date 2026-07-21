"use client";

import { useMemo, useState } from "react";
import { CalendarDays, Check, Clock, PackagePlus, Plus, RefreshCw, Settings, Truck } from "lucide-react";
import type { CatalogRow, LogisticsData, OrderRow, ProductTotal, TripRow } from "@/lib/logistics";

type Tab = "orders" | "trips" | "calendar" | "config";

const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });

export function LogisticsDashboard({ initialData, initialError, companyId, companyName, reviewMode = false }: { initialData: LogisticsData | null; initialError: string; companyId: string; companyName: string; reviewMode?: boolean }) {
  const [data, setData] = useState<LogisticsData | null>(initialData);
  const [error, setError] = useState(initialError);
  const [tab, setTab] = useState<Tab>("orders");
  const [selectedOrders, setSelectedOrders] = useState<string[]>([]);
  const [busy, setBusy] = useState("");

  function applyReviewAction(name: string, context: Record<string, unknown>) {
    if (!data) return false;
    if (name === "create_trip") {
      const ids = new Set((context.pedido_ids as string[]) || []);
      const selected = data.available_orders.filter((order) => ids.has(order.id));
      if (!selected.length) {
        setError("Selecciona pedidos para crear viaje.");
        return false;
      }
      const trip: TripRow = {
        id: `review-trip-${Date.now()}`,
        folio: nextTripFolio(data.trips),
        estado: "borrador",
        fecha_viaje: null,
        hora_inicio: null,
        hora_fin: null,
        duracion_minutos: data.duration_minutes_default || 120,
        vehiculo_id: null,
        driver_id: null,
        orders: selected,
        summary: summarizeOrders(selected)
      };
      setData({ ...data, available_orders: data.available_orders.filter((order) => !ids.has(order.id)), trips: [...data.trips, trip] });
      setError("");
      return true;
    }
    if (name === "manage_trip") {
      setData({
        ...data,
        trips: data.trips.map((trip) => {
          if (trip.id !== context.trip_id) return trip;
          const updated = {
            ...trip,
            fecha_viaje: (context.fecha_viaje as string | null) || null,
            hora_inicio: (context.hora_inicio as string | null) || null,
            duracion_minutos: Number(context.duracion_minutos || trip.duracion_minutos || 120),
            vehiculo_id: (context.vehiculo_id as string | null) || null,
            driver_id: (context.driver_id as string | null) || null
          };
          return { ...updated, estado: tripStatus(updated), hora_fin: tripEndTime(updated) };
        })
      });
      setError("");
      return true;
    }
    if (name === "catalog_manage" && context.action === "create") {
      const catalog = context.catalog === "driver" ? "drivers" : "vehicles";
      const prefix = catalog === "drivers" ? "CHO" : "VEH";
      const row = { id: `review-${catalog}-${Date.now()}`, folio: `${prefix}-TMP`, nombre: String(context.nombre || "") };
      setData({ ...data, catalogs: { ...data.catalogs, [catalog]: [...data.catalogs[catalog], row] } });
      setError("");
      return true;
    }
    setError("Accion no disponible en revision.");
    return false;
  }

  async function updateOrderLogistics(tripId: string, order: OrderRow, patch: Partial<OrderRow>) {
    const nextOrder = { ...order, ...patch };
    if (reviewMode) {
      if (!data) return;
      setData({
        ...data,
        trips: data.trips.map((trip) => {
          if (trip.id !== tripId) return trip;
          const orders = trip.orders.map((row) => (row.id === order.id ? nextOrder : row));
          return { ...trip, orders, summary: summarizeOrders(orders) };
        })
      });
      return;
    }
    const tripOrderId = String((order as OrderRow & { trip_order?: { id?: string } }).trip_order?.id || "");
    if (!tripOrderId) {
      setError("No se encontro la liga del pedido al viaje.");
      return;
    }
    await action("manage_trip", {
      action: "update_order_logistics",
      trip_order_id: tripOrderId,
      ...(patch.peso_kg !== undefined ? { peso_override_kg: patch.peso_kg } : {}),
      ...(patch.fecha_entrega !== undefined ? { fecha_entrega_override: patch.fecha_entrega || null } : {})
    });
  }

  async function refresh() {
    if (reviewMode) return;
    setBusy("refresh");
    const res = await fetch(`/api/logistics?company_id=${encodeURIComponent(companyId)}`);
    const json = await res.json().catch(() => ({}));
    setBusy("");
    if (!res.ok || !json.ok) {
      setError(json.error || "No se pudo actualizar");
      return;
    }
    setData(json.data);
    setError("");
  }

  async function action(name: string, context: Record<string, unknown>) {
    if (reviewMode) {
      return applyReviewAction(name, context);
    }
    setBusy(name);
    const res = await fetch("/api/logistics/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: name, company_id: companyId, context, dry_run: false })
    });
    const json = await res.json().catch(() => ({}));
    setBusy("");
    if (!res.ok || !json.ok) {
      setError(json.error || "Accion fallida");
      return false;
    }
    await refresh();
    return true;
  }

  async function createTrip() {
    if (!selectedOrders.length) return;
    const ok = await action("create_trip", { pedido_ids: selectedOrders });
    if (ok) {
      setSelectedOrders([]);
      setTab("trips");
    }
  }

  const orders = data?.available_orders || [];
  const trips = data?.trips || [];

  return (
    <div className="mx-auto max-w-7xl px-3 py-4 sm:px-5">
      <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{companyName}</h1>
          <p className="text-sm text-slate-600">{orders.length} pedidos pendientes · {trips.length} viajes activos</p>
        </div>
        <button onClick={refresh} className="btn-soft" disabled={busy === "refresh"}>
          <RefreshCw size={16} />
          Actualizar
        </button>
      </section>

      {error && <div className="mt-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      <nav className="mt-4 grid grid-cols-4 gap-2">
        <TabButton active={tab === "orders"} onClick={() => setTab("orders")} icon={<PackagePlus size={17} />} label="Pedidos" />
        <TabButton active={tab === "trips"} onClick={() => setTab("trips")} icon={<Truck size={17} />} label="Viajes" />
        <TabButton active={tab === "calendar"} onClick={() => setTab("calendar")} icon={<CalendarDays size={17} />} label="Calendario" />
        <TabButton active={tab === "config"} onClick={() => setTab("config")} icon={<Settings size={17} />} label="Config" />
      </nav>

      <section className="mt-4">
        {tab === "orders" && (
          <OrdersTab
            orders={orders}
            selectedOrders={selectedOrders}
            setSelectedOrders={setSelectedOrders}
            createTrip={createTrip}
            busy={busy}
          />
        )}
        {tab === "trips" && <TripsTab trips={trips} catalogs={data?.catalogs || { vehicles: [], drivers: [], product_config: [] }} action={action} busy={busy} reviewMode={reviewMode} updateOrderLogistics={updateOrderLogistics} />}
        {tab === "calendar" && <CalendarTab trips={trips} />}
        {tab === "config" && <ConfigTab catalogs={data?.catalogs || { vehicles: [], drivers: [], product_config: [] }} action={action} busy={busy} />}
      </section>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button onClick={onClick} className={`flex min-h-12 items-center justify-center gap-2 rounded-md border px-2 text-sm font-semibold ${active ? "border-ink bg-ink text-white" : "border-line bg-white text-ink"}`}>
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function OrdersTab({ orders, selectedOrders, setSelectedOrders, createTrip, busy }: { orders: OrderRow[]; selectedOrders: string[]; setSelectedOrders: (rows: string[]) => void; createTrip: () => void; busy: string }) {
  function toggle(id: string) {
    setSelectedOrders(selectedOrders.includes(id) ? selectedOrders.filter((item) => item !== id) : [...selectedOrders, id]);
  }
  return (
    <div>
      <div className="sticky top-[116px] z-20 flex items-center justify-between gap-3 border border-line bg-white p-3 shadow-sm sm:top-[65px]">
        <p className="text-sm font-semibold text-ink">{selectedOrders.length} seleccionados</p>
        <button onClick={createTrip} className="btn-primary" disabled={!selectedOrders.length || Boolean(busy)}>
          <Plus size={16} />
          Crear viaje
        </button>
      </div>
      <div className="mt-3 grid gap-3">
        {orders.map((order) => (
          <button key={order.id} onClick={() => toggle(order.id)} className={`border bg-white p-3 text-left shadow-sm ${selectedOrders.includes(order.id) ? "border-steel ring-2 ring-steel/20" : "border-line"}`}>
            <div className="flex items-start gap-3">
              <span className={`mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded border ${selectedOrders.includes(order.id) ? "border-steel bg-steel text-white" : "border-line"}`}>
                {selectedOrders.includes(order.id) && <Check size={15} />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <p className="font-mono text-sm font-bold text-ink">{order.folio}</p>
                  <p className="truncate text-sm font-semibold text-slate-800">{order.customer_name_snapshot || "Sin cliente"}</p>
                  <p className="text-sm text-slate-500">{order.city || "Sin ciudad"}</p>
                </div>
                <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-5">
                  <span>{order.fecha_entrega || "Sin fecha"}</span>
                  <span>{number.format(order.peso_kg || 0)} kg</span>
                  <span>{order.partida_1 || "-"}</span>
                  <span>{order.partida_2 || order.partida_3 || "-"}</span>
                  <span className="font-semibold text-ink">{money.format(order.importe || 0)}</span>
                </div>
              </div>
            </div>
          </button>
        ))}
        {!orders.length && <Empty label="Sin pedidos disponibles" />}
      </div>
    </div>
  );
}

function TripsTab({
  trips,
  catalogs,
  action,
  busy,
  reviewMode,
  updateOrderLogistics
}: {
  trips: TripRow[];
  catalogs: LogisticsData["catalogs"];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
  reviewMode?: boolean;
  updateOrderLogistics: (tripId: string, order: OrderRow, patch: Partial<OrderRow>) => Promise<void>;
}) {
  return (
    <div className="grid gap-4">
      {trips.map((trip) => (
        <TripPanel key={trip.id} trip={trip} catalogs={catalogs} action={action} busy={busy} reviewMode={reviewMode} updateOrderLogistics={updateOrderLogistics} />
      ))}
      {!trips.length && <Empty label="Sin viajes activos" />}
    </div>
  );
}

function TripPanel({
  trip,
  catalogs,
  action,
  busy,
  updateOrderLogistics
}: {
  trip: TripRow;
  catalogs: LogisticsData["catalogs"];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
  reviewMode?: boolean;
  updateOrderLogistics: (tripId: string, order: OrderRow, patch: Partial<OrderRow>) => Promise<void>;
}) {
  const [fecha, setFecha] = useState(trip.fecha_viaje || "");
  const [hora, setHora] = useState((trip.hora_inicio || "").slice(0, 5));
  const [duracion, setDuracion] = useState(String(trip.duracion_minutos || 120));
  const [vehicle, setVehicle] = useState(trip.vehiculo_id || "");
  const [driver, setDriver] = useState(trip.driver_id || "");
  async function save() {
    await action("manage_trip", { trip_id: trip.id, fecha_viaje: fecha || null, hora_inicio: hora || null, duracion_minutos: Number(duracion || 120), vehiculo_id: vehicle || null, driver_id: driver || null });
  }
  return (
    <article className="border border-line bg-white shadow-sm">
      <header className="border-b border-line p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-lg font-bold text-ink">{trip.folio}</p>
            <p className="text-sm text-slate-600">{trip.summary.orders_count} pedidos · {number.format(trip.summary.peso_total_kg)} kg · {money.format(trip.summary.importe_total)}</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase text-slate-600">{trip.estado}</span>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-5">
          <input value={fecha} onChange={(event) => setFecha(event.target.value)} type="date" className="input" />
          <input value={hora} onChange={(event) => setHora(event.target.value)} type="time" className="input" />
          <input value={duracion} onChange={(event) => setDuracion(event.target.value)} type="number" min="15" step="15" className="input" />
          <Select value={vehicle} onChange={setVehicle} rows={catalogs.vehicles} placeholder="Vehiculo" />
          <Select value={driver} onChange={setDriver} rows={catalogs.drivers} placeholder="Chofer" />
        </div>
        <button onClick={save} disabled={Boolean(busy)} className="btn-soft mt-3 w-full sm:w-auto">
          <Clock size={16} />
          Guardar programacion
        </button>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Pedido</th>
              <th className="px-3 py-2">Cliente</th>
              <th className="px-3 py-2">Fecha entrega</th>
              <th className="px-3 py-2">Peso</th>
              <th className="px-3 py-2">Partida 1</th>
              <th className="px-3 py-2">Partida 2</th>
              <th className="px-3 py-2">Partida 3</th>
              <th className="px-3 py-2">Otras</th>
              <th className="px-3 py-2 text-right">Importe</th>
            </tr>
          </thead>
          <tbody>
            {trip.orders.map((order) => (
              <tr key={order.id} className="border-t border-line">
                <td className="px-3 py-2 font-mono font-semibold">{order.folio}</td>
                <td className="px-3 py-2">{order.customer_name_snapshot}</td>
                <td className="px-3 py-2">
                  <input
                    type="date"
                    value={order.fecha_entrega || ""}
                    onChange={(event) => updateOrderLogistics(trip.id, order, { fecha_entrega: event.target.value })}
                    className="input h-9 min-w-36"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={String(order.peso_kg || 0)}
                    onChange={(event) => updateOrderLogistics(trip.id, order, { peso_kg: Number(event.target.value || 0) })}
                    className="input h-9 w-32"
                  />
                </td>
                <td className="px-3 py-2">{order.partida_1 || "-"}</td>
                <td className="px-3 py-2">{order.partida_2 || "-"}</td>
                <td className="px-3 py-2">{order.partida_3 || "-"}</td>
                <td className="px-3 py-2">{order.otras_partidas || "-"}</td>
                <td className="px-3 py-2 text-right font-semibold">{money.format(order.importe || 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer className="grid gap-3 border-t border-line bg-slate-50 p-3 sm:grid-cols-2">
        <div className="text-sm font-semibold text-ink">Total peso {number.format(trip.summary.peso_total_kg)} kg</div>
        <div className="text-sm font-semibold text-ink sm:text-right">Total importe {money.format(trip.summary.importe_total)}</div>
        <div className="sm:col-span-2">
          <ProductTotals products={trip.summary.product_totals} />
        </div>
      </footer>
    </article>
  );
}

function CalendarTab({ trips }: { trips: TripRow[] }) {
  const days = useMemo(() => {
    const grouped = new Map<string, TripRow[]>();
    trips.filter((trip) => trip.fecha_viaje).forEach((trip) => {
      const key = String(trip.fecha_viaje);
      grouped.set(key, [...(grouped.get(key) || []), trip]);
    });
    return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [trips]);
  return (
    <div className="grid gap-4">
      {days.map(([day, rows]) => (
        <section key={day} className="border border-line bg-white">
          <h2 className="border-b border-line px-3 py-2 text-lg font-semibold">{day}</h2>
          <div className="grid gap-3 p-3">
            {rows.map((trip) => (
              <div key={trip.id} className="border-l-4 border-steel bg-slate-50 p-3">
                <p className="font-mono font-bold">{trip.hora_inicio?.slice(0, 5) || "--:--"}-{trip.hora_fin || "--:--"} · {trip.folio}</p>
                <p className="text-sm text-slate-600">{trip.summary.orders_count} pedidos · {number.format(trip.summary.peso_total_kg)} kg · {money.format(trip.summary.importe_total)}</p>
                <ProductTotals products={trip.summary.key_products} compact />
              </div>
            ))}
          </div>
        </section>
      ))}
      {!days.length && <Empty label="Sin viajes programados" />}
    </div>
  );
}

function ConfigTab({ catalogs, action, busy }: { catalogs: LogisticsData["catalogs"]; action: (name: string, context: Record<string, unknown>) => Promise<boolean>; busy: string }) {
  const [vehicle, setVehicle] = useState("");
  const [driver, setDriver] = useState("");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="border border-line bg-white p-3">
        <h2 className="text-lg font-semibold">Vehiculos</h2>
        <div className="mt-3 flex gap-2">
          <input value={vehicle} onChange={(event) => setVehicle(event.target.value)} className="input" placeholder="Nombre" />
          <button disabled={!vehicle || Boolean(busy)} onClick={async () => { if (await action("catalog_manage", { action: "create", catalog: "vehicle", nombre: vehicle })) setVehicle(""); }} className="btn-primary px-3">
            <Plus size={16} />
          </button>
        </div>
        <CatalogList rows={catalogs.vehicles} />
      </section>
      <section className="border border-line bg-white p-3">
        <h2 className="text-lg font-semibold">Choferes</h2>
        <div className="mt-3 flex gap-2">
          <input value={driver} onChange={(event) => setDriver(event.target.value)} className="input" placeholder="Nombre" />
          <button disabled={!driver || Boolean(busy)} onClick={async () => { if (await action("catalog_manage", { action: "create", catalog: "driver", nombre: driver })) setDriver(""); }} className="btn-primary px-3">
            <Plus size={16} />
          </button>
        </div>
        <CatalogList rows={catalogs.drivers} />
      </section>
      <section className="border border-line bg-white p-3 lg:col-span-2">
        <h2 className="text-lg font-semibold">Productos clave</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {catalogs.product_config.map((row) => (
            <span key={row.id} className="rounded-full border border-line px-3 py-1 text-sm">{row.product_label}</span>
          ))}
          {!catalogs.product_config.length && <span className="text-sm text-slate-500">Sin productos configurados</span>}
        </div>
      </section>
    </div>
  );
}

function Select({ value, onChange, rows, placeholder, disabled = false }: { value: string; onChange: (value: string) => void; rows: CatalogRow[]; placeholder: string; disabled?: boolean }) {
  return (
    <select value={value} onChange={(event) => onChange(event.target.value)} className="input" disabled={disabled}>
      <option value="">{placeholder}</option>
      {rows.map((row) => (
        <option key={row.id} value={row.id}>{row.nombre}</option>
      ))}
    </select>
  );
}

function ProductTotals({ products, compact = false }: { products: { product_name: string; quantity: number; unit?: string | null }[]; compact?: boolean }) {
  return (
    <div className={`flex flex-wrap gap-2 ${compact ? "mt-2" : ""}`}>
      {products.slice(0, compact ? 4 : 12).map((product) => (
        <span key={product.product_name} className="rounded-full border border-line bg-white px-2 py-1 text-xs font-semibold text-slate-700">
          {product.product_name}: {number.format(product.quantity)} {product.unit || ""}
        </span>
      ))}
    </div>
  );
}

function CatalogList({ rows }: { rows: CatalogRow[] }) {
  return (
    <div className="mt-3 divide-y divide-line border border-line">
      {rows.map((row) => (
        <div key={row.id} className="px-3 py-2 text-sm">
          <p className="font-semibold">{row.nombre}</p>
          <p className="text-xs text-slate-500">{row.placa || row.telefono || row.tipo || row.folio}</p>
        </div>
      ))}
      {!rows.length && <p className="px-3 py-2 text-sm text-slate-500">Sin registros</p>}
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <div className="border border-dashed border-line bg-white px-4 py-8 text-center text-sm text-slate-500">{label}</div>;
}

function summarizeOrders(orders: OrderRow[]) {
  const totals = new Map<string, ProductTotal>();
  let peso = 0;
  let importe = 0;
  for (const order of orders) {
    peso += Number(order.peso_kg || 0);
    importe += Number(order.importe || 0);
    const items = ((order as OrderRow & { items?: Record<string, unknown>[] }).items || []);
    for (const item of items) {
      const productId = String(item.inventory_product_id || item.product_id || item.description || item.product_name_snapshot || "producto");
      const productName = String(item.product_name_snapshot || item.description || "Producto");
      const current = totals.get(productId) || { product_id: productId, product_name: productName, quantity: 0, unit: String(item.unit || ""), weight_kg_total: 0, line_total: 0 };
      current.quantity += Number(item.quantity || 0);
      current.weight_kg_total += Number(item.weight_kg_total || 0);
      current.line_total += Number(item.line_total || 0);
      totals.set(productId, current);
    }
  }
  const productTotals = Array.from(totals.values()).sort((a, b) => b.quantity - a.quantity || b.line_total - a.line_total);
  return { orders_count: orders.length, peso_total_kg: Math.round(peso * 100) / 100, importe_total: Math.round(importe * 100) / 100, key_products: productTotals.slice(0, 4), product_totals: productTotals };
}

function nextTripFolio(trips: TripRow[]) {
  const max = trips.reduce((value, trip) => {
    const match = /^VIA-(\d+)$/.exec(trip.folio || "");
    return match ? Math.max(value, Number(match[1])) : value;
  }, 0);
  return `VIA-${String(max + 1).padStart(5, "0")}`;
}

function tripEndTime(trip: Partial<TripRow>) {
  if (!trip.hora_inicio) return null;
  const [hours, minutes] = String(trip.hora_inicio).slice(0, 5).split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null;
  const start = new Date(2000, 0, 1, hours, minutes);
  start.setMinutes(start.getMinutes() + Number(trip.duracion_minutos || 120));
  return `${String(start.getHours()).padStart(2, "0")}:${String(start.getMinutes()).padStart(2, "0")}`;
}

function tripStatus(trip: Partial<TripRow>) {
  if (trip.estado && !["borrador", "programado"].includes(trip.estado)) return trip.estado;
  return trip.fecha_viaje && trip.hora_inicio && trip.duracion_minutos && trip.vehiculo_id && trip.driver_id ? "programado" : "borrador";
}
