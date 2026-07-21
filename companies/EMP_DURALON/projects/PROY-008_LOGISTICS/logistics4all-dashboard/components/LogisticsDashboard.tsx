"use client";

import { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Archive, CalendarDays, Check, Clock, PackagePlus, Plus, RefreshCw, Save, Settings, Truck } from "lucide-react";
import type { CatalogRow, LogisticsData, OrderRow, ProductTotal, TripRow } from "@/lib/logistics";

type Tab = "orders" | "scheduled_orders" | "trips" | "calendar" | "completed_trips" | "config";

const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });
const closedTripStatuses = new Set(["completado", "cancelado"]);

export function LogisticsDashboard({ initialData, initialError, companyId, companyName, reviewMode = false }: { initialData: LogisticsData | null; initialError: string; companyId: string; companyName: string; reviewMode?: boolean }) {
  const [data, setData] = useState<LogisticsData | null>(initialData);
  const [error, setError] = useState(initialError);
  const [tab, setTab] = useState<Tab>("orders");
  const [selectedOrders, setSelectedOrders] = useState<string[]>([]);
  const [targetTripId, setTargetTripId] = useState("");
  const [busy, setBusy] = useState("");

  function applyReviewAction(name: string, context: Record<string, unknown>) {
    if (!data) return false;
    if (name === "create_trip") {
      const ids = new Set((context.pedido_ids as string[]) || []);
      const selected = data.available_orders.filter((order) => ids.has(order.id));
      if (!selected.length && !context.allow_empty) {
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
      setData({
        ...data,
        available_orders: data.available_orders.map((order) => (ids.has(order.id) ? { ...order, logistics_assignment: { trip_id: trip.id, trip_folio: trip.folio, trip_estado: trip.estado } } : order)),
        trips: [...data.trips, trip]
      });
      setError("");
      return true;
    }
    if (name === "assign_orders") {
      const ids = new Set((context.pedido_ids as string[]) || []);
      const tripId = String(context.trip_id || "");
      if (context.action === "remove") {
        setData({
          ...data,
          available_orders: data.available_orders.map((order) => (ids.has(order.id) ? { ...order, logistics_assignment: undefined } : order)),
          trips: data.trips.map((trip) => {
            if (trip.id !== tripId) return trip;
            const orders = trip.orders.filter((order) => !ids.has(order.id));
            return { ...trip, orders, summary: summarizeOrders(orders) };
          })
        });
        setError("");
        return true;
      }
      const target = data.trips.find((trip) => trip.id === tripId);
      const selected = data.available_orders.filter((order) => ids.has(order.id));
      if (!target || !selected.length) {
        setError("Selecciona pedidos y viaje destino.");
        return false;
      }
      const targetOrders = [...target.orders.filter((order) => !ids.has(order.id)), ...selected];
      setData({
        ...data,
        available_orders: data.available_orders.map((order) => (ids.has(order.id) ? { ...order, logistics_assignment: { trip_id: target.id, trip_folio: target.folio, trip_estado: target.estado, fecha_viaje: target.fecha_viaje, hora_inicio: target.hora_inicio } } : order)),
        trips: data.trips.map((trip) => {
          if (trip.id === target.id) return { ...trip, orders: targetOrders, summary: summarizeOrders(targetOrders) };
          return { ...trip, orders: trip.orders.filter((order) => !ids.has(order.id)), summary: summarizeOrders(trip.orders.filter((order) => !ids.has(order.id))) };
        })
      });
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
          return { ...updated, estado: (context.estado as string) || tripStatus(updated), hora_fin: tripEndTime(updated) };
        })
      });
      setError("");
      return true;
    }
    if (name === "catalog_manage" && context.action === "create") {
      const catalog = context.catalog === "driver" ? "drivers" : "vehicles";
      const prefix = catalog === "drivers" ? "CHO" : "VEH";
      const row = { id: `review-${catalog}-${Date.now()}`, folio: `${prefix}-TMP`, nombre: String(context.nombre || ""), tipo: context.tipo as string, placa: context.placa as string, telefono: context.telefono as string, capacidad_peso_kg: Number(context.capacidad_peso_kg || 0), activo: true };
      setData({ ...data, catalogs: { ...data.catalogs, [catalog]: [...data.catalogs[catalog], row] } });
      setError("");
      return true;
    }
    if (name === "catalog_manage" && context.action === "update") {
      const catalog = context.catalog === "driver" ? "drivers" : "vehicles";
      setData({
        ...data,
        catalogs: {
          ...data.catalogs,
          [catalog]: data.catalogs[catalog].map((row) => (row.id === context.id ? { ...row, ...context } : row))
        }
      });
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
    const res = await fetch(`/api/logistics?company_id=${encodeURIComponent(companyId)}`, { credentials: "same-origin" });
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
      credentials: "same-origin",
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

  async function createEmptyTrip() {
    const ok = await action("create_trip", { pedido_ids: [], allow_empty: true });
    if (ok) {
      setSelectedOrders([]);
      setTargetTripId("");
      setTab("trips");
    }
  }

  async function assignToExistingTrip() {
    if (!selectedOrders.length || !targetTripId) return;
    const ok = await action("assign_orders", { trip_id: targetTripId, pedido_ids: selectedOrders });
    if (ok) {
      setSelectedOrders([]);
      setTargetTripId("");
      setTab("trips");
    }
  }

  const orders = data?.available_orders || [];
  const trips = data?.trips || [];
  const activeTrips = trips.filter((trip) => !closedTripStatuses.has(trip.estado));
  const completedTrips = trips.filter((trip) => trip.estado === "completado");
  const pendingOrders = orders.filter((order) => !order.logistics_assignment);
  const scheduledOrders = orders.filter((order) => {
    const assignment = order.logistics_assignment;
    return assignment && !closedTripStatuses.has(String(assignment.trip_estado || ""));
  });

  return (
    <div className="mx-auto max-w-7xl px-3 py-4 sm:px-5">
      <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{companyName}</h1>
          <p className="text-sm text-slate-600">{pendingOrders.length} pedidos por programar · {activeTrips.length} viajes vivos · {completedTrips.length} terminados</p>
        </div>
        <button onClick={refresh} className="btn-soft" disabled={busy === "refresh"}>
          <RefreshCw size={16} />
          Actualizar
        </button>
      </section>

      {error && <div className="mt-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      <nav className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
        <TabButton active={tab === "orders"} onClick={() => setTab("orders")} icon={<PackagePlus size={17} />} label="Pedidos" />
        <TabButton active={tab === "scheduled_orders"} onClick={() => setTab("scheduled_orders")} icon={<Clock size={17} />} label="Programados" />
        <TabButton active={tab === "trips"} onClick={() => setTab("trips")} icon={<Truck size={17} />} label="Viajes" />
        <TabButton active={tab === "calendar"} onClick={() => setTab("calendar")} icon={<CalendarDays size={17} />} label="Calendario" />
        <TabButton active={tab === "completed_trips"} onClick={() => setTab("completed_trips")} icon={<Archive size={17} />} label="Terminados" />
        <TabButton active={tab === "config"} onClick={() => setTab("config")} icon={<Settings size={17} />} label="Config" />
      </nav>

      <section className="mt-4">
        {tab === "orders" && (
          <OrdersTab
            orders={pendingOrders}
            selectedOrders={selectedOrders}
            setSelectedOrders={setSelectedOrders}
            createTrip={createTrip}
            createEmptyTrip={createEmptyTrip}
            assignToExistingTrip={assignToExistingTrip}
            trips={activeTrips}
            targetTripId={targetTripId}
            setTargetTripId={setTargetTripId}
            busy={busy}
          />
        )}
        {tab === "scheduled_orders" && <ScheduledOrdersTab orders={scheduledOrders} trips={activeTrips} action={action} busy={busy} />}
        {tab === "trips" && <TripsTab trips={activeTrips} catalogs={data?.catalogs || { vehicles: [], drivers: [], product_config: [] }} action={action} busy={busy} reviewMode={reviewMode} updateOrderLogistics={updateOrderLogistics} createEmptyTrip={createEmptyTrip} />}
        {tab === "calendar" && <CalendarTab trips={activeTrips} catalogs={data?.catalogs || { vehicles: [], drivers: [], product_config: [] }} companyId={companyId} refresh={refresh} setError={setError} />}
        {tab === "completed_trips" && <CompletedTripsTab trips={completedTrips} action={action} busy={busy} />}
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

function OrdersTab({
  orders,
  selectedOrders,
  setSelectedOrders,
  createTrip,
  createEmptyTrip,
  assignToExistingTrip,
  trips,
  targetTripId,
  setTargetTripId,
  busy
}: {
  orders: OrderRow[];
  selectedOrders: string[];
  setSelectedOrders: (rows: string[]) => void;
  createTrip: () => void;
  createEmptyTrip: () => void;
  assignToExistingTrip: () => void;
  trips: TripRow[];
  targetTripId: string;
  setTargetTripId: (value: string) => void;
  busy: string;
}) {
  function toggle(id: string) {
    setSelectedOrders(selectedOrders.includes(id) ? selectedOrders.filter((item) => item !== id) : [...selectedOrders, id]);
  }
  const activeTrips = trips.filter((trip) => !["completado", "cancelado"].includes(trip.estado));
  const cityGroups = useMemo(() => {
    const grouped = new Map<string, OrderRow[]>();
    for (const order of orders) {
      const city = String(order.city || "Sin ciudad").trim() || "Sin ciudad";
      grouped.set(city, [...(grouped.get(city) || []), order]);
    }
    return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [orders]);
  return (
    <div>
      <div className="sticky top-[116px] z-20 grid gap-3 border border-line bg-white p-3 shadow-sm sm:top-[65px] lg:grid-cols-[1fr_auto_auto_auto] lg:items-center">
        <p className="text-sm font-semibold text-ink">{selectedOrders.length} seleccionados</p>
        <div className="flex min-w-0 gap-2">
          <select value={targetTripId} onChange={(event) => setTargetTripId(event.target.value)} className="input min-w-0" disabled={!activeTrips.length}>
            <option value="">Viaje existente</option>
            {activeTrips.map((trip) => (
              <option key={trip.id} value={trip.id}>{trip.folio} · {trip.estado}</option>
            ))}
          </select>
          <button onClick={assignToExistingTrip} className="btn-soft whitespace-nowrap" disabled={!selectedOrders.length || !targetTripId || Boolean(busy)}>
            Agregar
          </button>
        </div>
        <button onClick={createTrip} className="btn-primary" disabled={!selectedOrders.length || Boolean(busy)}>
          <Plus size={16} />
          Nuevo viaje
        </button>
        <button onClick={createEmptyTrip} className="btn-soft" disabled={Boolean(busy)}>
          <Plus size={16} />
          Viaje vacio
        </button>
      </div>
      <div className="mt-3 grid gap-4">
        {cityGroups.map(([city, rows]) => {
          const totalPeso = rows.reduce((sum, order) => sum + Number(order.peso_kg || 0), 0);
          const totalImporte = rows.reduce((sum, order) => sum + Number(order.importe || 0), 0);
          return (
            <section key={city} className="border border-line bg-white shadow-sm">
              <header className="flex flex-col gap-1 border-b border-line bg-slate-50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-sm font-bold text-ink">{city}</h2>
                <p className="text-xs font-semibold text-slate-600">{rows.length} pedidos · {number.format(totalPeso)} kg · {money.format(totalImporte)}</p>
              </header>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1120px] border-collapse text-xs">
                  <thead className="bg-white text-left uppercase text-slate-500">
                    <tr>
                      <th className="px-2 py-2">Sel</th>
                      <th className="px-2 py-2">Pedido</th>
                      <th className="px-2 py-2">Cliente</th>
                      <th className="px-2 py-2">Entrega</th>
                      <th className="px-2 py-2 text-right">Peso</th>
                      <th className="px-2 py-2 text-right">Importe</th>
                      <th className="px-2 py-2">Partidas completas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((order) => {
                      const selected = selectedOrders.includes(order.id);
                      return (
                        <tr key={order.id} onClick={() => toggle(order.id)} className={`cursor-pointer border-t border-line ${selected ? "bg-steel/10" : "hover:bg-slate-50"}`}>
                          <td className="px-2 py-2">
                            <span className={`flex h-6 w-6 items-center justify-center rounded border ${selected ? "border-steel bg-steel text-white" : "border-line bg-white"}`}>
                              {selected && <Check size={15} />}
                            </span>
                          </td>
                          <td className="px-2 py-2 font-mono font-bold text-ink">{order.folio}</td>
                          <td className="max-w-60 truncate px-2 py-2 font-semibold text-slate-800">{order.customer_name_snapshot || "Sin cliente"}</td>
                          <td className="px-2 py-2 text-slate-600">{order.fecha_entrega || "-"}</td>
                          <td className="px-2 py-2 text-right text-slate-700">{number.format(order.peso_kg || 0)} kg</td>
                          <td className="px-2 py-2 text-right font-semibold text-ink">{money.format(order.importe || 0)}</td>
                          <td className="px-2 py-2">
                            <OrderItemsInline items={order.items || []} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })}
        {false && orders.map((order) => (
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
                  {order.logistics_assignment ? (
                    <span className="rounded-full bg-steel/10 px-2 py-1 text-xs font-bold text-steel">{order.logistics_assignment.trip_folio} · {order.logistics_assignment.trip_estado}</span>
                  ) : (
                    <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700">Pendiente de viaje</span>
                  )}
                </div>
                {order.logistics_assignment && (
                  <div className="mt-2 grid gap-2 border border-steel/15 bg-steel/5 px-3 py-2 text-xs text-slate-700 sm:grid-cols-2 lg:grid-cols-4">
                    <span><strong className="text-ink">Viaje:</strong> {order.logistics_assignment.trip_folio} - {order.logistics_assignment.trip_estado}</span>
                    <span><strong className="text-ink">Fecha:</strong> {order.logistics_assignment.fecha_viaje || "Sin fecha"}</span>
                    <span><strong className="text-ink">Horario:</strong> {tripScheduleLabel(order.logistics_assignment)}</span>
                    <span><strong className="text-ink">Unidad:</strong> {order.logistics_assignment.vehiculo_nombre || "Sin vehiculo"}</span>
                    <span><strong className="text-ink">Chofer:</strong> {order.logistics_assignment.driver_nombre || "Sin chofer"}</span>
                    <span><strong className="text-ink">Duracion:</strong> {order.logistics_assignment.duracion_minutos || 0} min</span>
                  </div>
                )}
                <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-5">
                  <span>{order.fecha_entrega || "Sin fecha"}</span>
                  <span>{number.format(order.peso_kg || 0)} kg</span>
                  <span>{order.items?.length || 0} partidas</span>
                  <span>{order.city || "Sin ciudad"}</span>
                  <span className="font-semibold text-ink">{money.format(order.importe || 0)}</span>
                </div>
                <OrderItemsMiniTable items={order.items || []} />
              </div>
            </div>
          </button>
        ))}
        {!orders.length && <Empty label="Sin pedidos disponibles" />}
      </div>
    </div>
  );
}

function ScheduledOrdersTab({
  orders,
  trips,
  action,
  busy
}: {
  orders: OrderRow[];
  trips: TripRow[];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
}) {
  return (
    <div className="grid gap-3">
      {orders.map((order) => (
        <ScheduledOrderRow key={order.id} order={order} trips={trips} action={action} busy={busy} />
      ))}
      {!orders.length && <Empty label="Sin pedidos programados" />}
    </div>
  );
}

function ScheduledOrderRow({
  order,
  trips,
  action,
  busy
}: {
  order: OrderRow;
  trips: TripRow[];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
}) {
  const currentTripId = order.logistics_assignment?.trip_id || "";
  const [targetTripId, setTargetTripId] = useState("");
  const targetTrips = trips.filter((trip) => trip.id !== currentTripId);

  async function removeTrip() {
    if (!currentTripId) return;
    await action("assign_orders", { action: "remove", trip_id: currentTripId, pedido_ids: [order.id] });
  }

  async function moveTrip() {
    if (!targetTripId) return;
    await action("assign_orders", { trip_id: targetTripId, pedido_ids: [order.id] });
    setTargetTripId("");
  }

  return (
    <div className="border border-line bg-white p-3 shadow-sm">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <p className="font-mono text-sm font-bold text-ink">{order.folio}</p>
            <p className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-800">{order.customer_name_snapshot || "Sin cliente"}</p>
            <span className="rounded-full bg-steel/10 px-2 py-1 text-xs font-bold text-steel">
              {order.logistics_assignment?.trip_folio} · {order.logistics_assignment?.trip_estado}
            </span>
          </div>
          {order.logistics_assignment && (
            <div className="mt-2 grid gap-2 text-xs text-slate-700 sm:grid-cols-2 lg:grid-cols-4">
              <span><strong className="text-ink">Fecha:</strong> {order.logistics_assignment.fecha_viaje || "Sin fecha"}</span>
              <span><strong className="text-ink">Horario:</strong> {tripScheduleLabel(order.logistics_assignment)}</span>
              <span><strong className="text-ink">Unidad:</strong> {order.logistics_assignment.vehiculo_nombre || "Sin vehiculo"}</span>
              <span><strong className="text-ink">Chofer:</strong> {order.logistics_assignment.driver_nombre || "Sin chofer"}</span>
            </div>
          )}
          <div className="mt-3 grid gap-2 border border-line bg-slate-50 p-2 sm:grid-cols-[minmax(180px,1fr)_auto_auto]">
            <select value={targetTripId} onChange={(event) => setTargetTripId(event.target.value)} className="input h-9" disabled={!targetTrips.length || Boolean(busy)}>
              <option value="">Cambiar a otro viaje</option>
              {targetTrips.map((trip) => (
                <option key={trip.id} value={trip.id}>{trip.folio} · {trip.estado}</option>
              ))}
            </select>
            <button onClick={moveTrip} disabled={!targetTripId || Boolean(busy)} className="btn-soft min-h-9 px-3">
              Mover
            </button>
            <button onClick={removeTrip} disabled={!currentTripId || Boolean(busy)} className="btn-soft min-h-9 px-3">
              Quitar viaje
            </button>
          </div>
          <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-5">
            <span>{order.fecha_entrega || "Sin entrega"}</span>
            <span>{number.format(order.peso_kg || 0)} kg</span>
            <span>{order.items?.length || 0} partidas</span>
            <span>{order.city || "Sin ciudad"}</span>
            <span className="font-semibold text-ink">{money.format(order.importe || 0)}</span>
          </div>
          <OrderItemsMiniTable items={order.items || []} />
    </div>
  );
}

function OrderItemsInline({ items }: { items: NonNullable<OrderRow["items"]> }) {
  if (!items.length) return <span className="text-slate-400">Sin partidas</span>;
  return (
    <div className="grid gap-1">
      {items.map((item, index) => (
        <div key={item.id || item.folio || index} className="grid grid-cols-[minmax(180px,1fr)_70px_70px_90px] gap-2 border-b border-slate-100 pb-1 last:border-0 last:pb-0">
          <span className="truncate font-semibold text-slate-800">{item.product_name_snapshot || item.description || "Producto"}</span>
          <span className="text-right text-slate-600">{number.format(item.quantity || 0)} {item.unit || ""}</span>
          <span className="text-right text-slate-600">{number.format(item.weight_kg_total || 0)} kg</span>
          <span className="text-right font-semibold text-ink">{money.format(item.line_total || 0)}</span>
        </div>
      ))}
    </div>
  );
}

function OrderItemsMiniTable({ items }: { items: NonNullable<OrderRow["items"]> }) {
  if (!items.length) {
    return <div className="mt-2 border border-line bg-slate-50 px-3 py-2 text-xs text-slate-500">Sin partidas capturadas</div>;
  }
  return (
    <div className="mt-2 overflow-x-auto border border-line bg-white">
      <table className="w-full min-w-[620px] border-collapse text-[11px]">
        <thead className="bg-slate-50 text-left uppercase text-slate-500">
          <tr>
            <th className="px-2 py-1.5">Producto</th>
            <th className="px-2 py-1.5">Clave</th>
            <th className="px-2 py-1.5 text-right">Cant.</th>
            <th className="px-2 py-1.5">Unidad</th>
            <th className="px-2 py-1.5 text-right">Peso</th>
            <th className="px-2 py-1.5 text-right">Importe</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.id || item.folio || index} className="border-t border-line">
              <td className="max-w-64 truncate px-2 py-1.5 font-semibold text-slate-800">{item.product_name_snapshot || item.description || "Producto"}</td>
              <td className="px-2 py-1.5 font-mono text-slate-500">{item.product_folio_snapshot || "-"}</td>
              <td className="px-2 py-1.5 text-right text-slate-700">{number.format(item.quantity || 0)}</td>
              <td className="px-2 py-1.5 text-slate-600">{item.unit || "-"}</td>
              <td className="px-2 py-1.5 text-right text-slate-700">{number.format(item.weight_kg_total || 0)} kg</td>
              <td className="px-2 py-1.5 text-right font-semibold text-ink">{money.format(item.line_total || 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TripsTab({
  trips,
  catalogs,
  action,
  busy,
  reviewMode,
  updateOrderLogistics,
  createEmptyTrip
}: {
  trips: TripRow[];
  catalogs: LogisticsData["catalogs"];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
  reviewMode?: boolean;
  updateOrderLogistics: (tripId: string, order: OrderRow, patch: Partial<OrderRow>) => Promise<void>;
  createEmptyTrip: () => void;
}) {
  return (
    <div className="grid gap-4">
      <div className="flex justify-end">
        <button onClick={createEmptyTrip} disabled={Boolean(busy)} className="btn-soft">
          <Plus size={16} />
          Nuevo viaje vacio
        </button>
      </div>
      {trips.map((trip) => (
        <TripPanel key={trip.id} trip={trip} trips={trips} catalogs={catalogs} action={action} busy={busy} reviewMode={reviewMode} updateOrderLogistics={updateOrderLogistics} />
      ))}
      {!trips.length && <Empty label="Sin viajes activos" />}
    </div>
  );
}

function TripPanel({
  trip,
  trips,
  catalogs,
  action,
  busy,
  updateOrderLogistics
}: {
  trip: TripRow;
  trips: TripRow[];
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
  const [draftOrders, setDraftOrders] = useState<Record<string, { peso: string; fecha: string }>>({});
  function draftFor(order: OrderRow) {
    return draftOrders[order.id] || { peso: String(order.peso_kg ?? 0), fecha: order.fecha_entrega || "" };
  }
  function setDraft(order: OrderRow, patch: Partial<{ peso: string; fecha: string }>) {
    setDraftOrders((current) => ({ ...current, [order.id]: { ...draftFor(order), ...patch } }));
  }
  async function saveOrderDraft(order: OrderRow) {
    const draft = draftFor(order);
    const peso = draft.peso.trim() === "" ? 0 : Number(draft.peso);
    if (!Number.isFinite(peso)) return;
    await updateOrderLogistics(trip.id, order, { peso_kg: peso, fecha_entrega: draft.fecha || null });
  }
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
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <button onClick={save} disabled={Boolean(busy)} className="btn-soft w-full sm:w-auto">
            <Clock size={16} />
            Guardar programacion
          </button>
          <button onClick={() => action("manage_trip", { trip_id: trip.id, estado: "completado" })} disabled={Boolean(busy)} className="btn-primary w-full sm:w-auto">
            <Check size={16} />
            Terminar viaje
          </button>
        </div>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1080px] border-collapse text-sm">
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
              <th className="px-3 py-2 text-right">Cambios</th>
              <th className="px-3 py-2">Mover</th>
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
                    value={draftFor(order).fecha}
                    onChange={(event) => setDraft(order, { fecha: event.target.value })}
                    onBlur={() => saveOrderDraft(order)}
                    className="input h-9 min-w-36"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={draftFor(order).peso}
                    onChange={(event) => setDraft(order, { peso: event.target.value })}
                    onBlur={() => saveOrderDraft(order)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") event.currentTarget.blur();
                    }}
                    className="input h-9 w-32"
                  />
                </td>
                <td className="px-3 py-2">{order.partida_1 || "-"}</td>
                <td className="px-3 py-2">{order.partida_2 || "-"}</td>
                <td className="px-3 py-2">{order.partida_3 || "-"}</td>
                <td className="px-3 py-2">{order.otras_partidas || "-"}</td>
                <td className="px-3 py-2 text-right font-semibold">{money.format(order.importe || 0)}</td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => saveOrderDraft(order)} disabled={Boolean(busy)} className="btn-soft min-h-9 px-3">
                    Guardar
                  </button>
                </td>
                <td className="px-3 py-2">
                  <MoveOrderCell currentTripId={trip.id} order={order} trips={trips} action={action} busy={busy} />
                </td>
              </tr>
            ))}
            {!trip.orders.length && (
              <tr className="border-t border-line">
                <td colSpan={11} className="px-3 py-5 text-center text-sm text-slate-500">
                  Viaje vacio. Puedes mover pedidos aqui desde Pedidos programados o desde otro viaje.
                </td>
              </tr>
            )}
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

function MoveOrderCell({
  currentTripId,
  order,
  trips,
  action,
  busy
}: {
  currentTripId: string;
  order: OrderRow;
  trips: TripRow[];
  action: (name: string, context: Record<string, unknown>) => Promise<boolean>;
  busy: string;
}) {
  const [targetTripId, setTargetTripId] = useState("");
  const targetTrips = trips.filter((trip) => trip.id !== currentTripId && !["completado", "cancelado"].includes(trip.estado));

  async function move() {
    if (!targetTripId) return;
    const ok = await action("assign_orders", { trip_id: targetTripId, pedido_ids: [order.id] });
    if (ok) setTargetTripId("");
  }

  async function removeTrip() {
    await action("assign_orders", { action: "remove", trip_id: currentTripId, pedido_ids: [order.id] });
  }

  return (
    <div className="flex min-w-[360px] gap-2">
      <select value={targetTripId} onChange={(event) => setTargetTripId(event.target.value)} className="input h-9 min-w-0" disabled={!targetTrips.length || Boolean(busy)}>
        <option value="">Otro viaje</option>
        {targetTrips.map((trip) => (
          <option key={trip.id} value={trip.id}>{trip.folio}</option>
        ))}
      </select>
      <button onClick={move} disabled={!targetTripId || Boolean(busy)} className="btn-soft min-h-9 px-3">
        Mover
      </button>
      <button onClick={removeTrip} disabled={Boolean(busy)} className="btn-soft min-h-9 px-3">
        Sin viaje
      </button>
    </div>
  );
}

function CompletedTripsTab({ trips, action, busy }: { trips: TripRow[]; action: (name: string, context: Record<string, unknown>) => Promise<boolean>; busy: string }) {
  return (
    <div className="grid gap-4">
      {trips.map((trip) => (
        <article key={trip.id} className="border border-line bg-white shadow-sm">
          <header className="flex flex-col gap-3 border-b border-line p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-lg font-bold text-ink">{trip.folio}</p>
              <p className="text-sm text-slate-600">
                {trip.fecha_viaje || "Sin fecha"} · {trip.hora_inicio?.slice(0, 5) || "--:--"}-{trip.hora_fin || "--:--"} · {trip.summary.orders_count} pedidos · {number.format(trip.summary.peso_total_kg)} kg · {money.format(trip.summary.importe_total)}
              </p>
            </div>
            <button onClick={() => action("manage_trip", { trip_id: trip.id, estado: "programado" })} disabled={Boolean(busy)} className="btn-soft w-full sm:w-auto">
              Regresar a viajes
            </button>
          </header>
          <CalendarProductMatrix trip={trip} />
        </article>
      ))}
      {!trips.length && <Empty label="Sin viajes terminados" />}
    </div>
  );
}

function CalendarTab({
  trips,
  catalogs,
  companyId,
  refresh,
  setError
}: {
  trips: TripRow[];
  catalogs: LogisticsData["catalogs"];
  companyId: string;
  refresh: () => Promise<void>;
  setError: (value: string) => void;
}) {
  const days = useMemo(() => {
    const grouped = new Map<string, TripRow[]>();
    trips.filter((trip) => trip.fecha_viaje).forEach((trip) => {
      const key = String(trip.fecha_viaje);
      grouped.set(key, [...(grouped.get(key) || []), trip]);
    });
    return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [trips]);
  const vehicleIndex = useMemo(() => new Map(catalogs.vehicles.map((row, index) => [row.id, index])), [catalogs.vehicles]);

  async function remisionarTrip(trip: TripRow, hidePrices: boolean) {
    if (!trip.orders.length) return;
    const ok = window.confirm(`Remisionar ${trip.orders.length} pedidos de ${trip.folio}?`);
    if (!ok) return;
    setError("");
    const remisiones: string[] = [];
    for (const order of trip.orders) {
      const res = await fetch("/api/logistics/action", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "pedido_to_remision",
          company_id: companyId,
          dry_run: false,
          context: {
            pedido_id: order.id,
            document_date: trip.fecha_viaje || undefined,
            notes: `Remision generada desde viaje ${trip.folio}`
          }
        })
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || !json.ok) {
        setError(json.error || `No se pudo remisionar ${order.folio}`);
        await refresh();
        return;
      }
      const folio = String(json.data?.remision?.folio || json.data?.remision?.document?.folio || "");
      if (folio) remisiones.push(folio);
    }
    await refresh();
    for (const folio of remisiones) {
      await openRemisionPdf(companyId, folio, hidePrices);
    }
  }
  return (
    <div className="grid gap-4">
      {days.map(([day, rows]) => (
        <section key={day} className="border border-line bg-white">
          <header className="flex flex-col gap-2 border-b border-line px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold">{day}</h2>
            <button onClick={() => openLogisticsDayPdf(day, rows, catalogs)} className="btn-soft w-full sm:w-auto">
              PDF del dia
            </button>
          </header>
          <div className="grid gap-3 p-3">
            {rows.map((trip) => (
              <div key={trip.id} className="border-l-4 p-3" style={vehicleColorStyle(vehicleIndex.get(String(trip.vehiculo_id || "")) ?? 0)}>
                <p className="font-mono font-bold">{trip.hora_inicio?.slice(0, 5) || "--:--"}-{trip.hora_fin || "--:--"} · {trip.folio}</p>
                <p className="text-sm text-slate-600">{trip.summary.orders_count} pedidos · {number.format(trip.summary.peso_total_kg)} kg · {money.format(trip.summary.importe_total)}</p>
                <p className="text-xs font-semibold text-slate-600">{vehicleName(catalogs.vehicles, trip.vehiculo_id) || "Sin vehiculo"}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button onClick={() => remisionarTrip(trip, false)} className="btn-soft px-3 text-xs">Remisionar $</button>
                  <button onClick={() => remisionarTrip(trip, true)} className="btn-soft px-3 text-xs">Remisionar sin $</button>
                </div>
                <ProductTotals products={trip.summary.key_products} compact />
                <CalendarProductMatrix trip={trip} />
              </div>
            ))}
          </div>
        </section>
      ))}
      {!days.length && <Empty label="Sin viajes programados" />}
    </div>
  );
}

function CalendarProductMatrix({ trip }: { trip: TripRow }) {
  const products = topTripProducts(trip, 6);
  return (
    <div className="mt-3 overflow-x-auto border border-line bg-white">
      <table className="w-full min-w-[900px] border-collapse text-[11px]">
        <thead className="bg-slate-50 text-left uppercase text-slate-500">
          <tr>
            <th className="px-2 py-2">Pedido</th>
            <th className="px-2 py-2">Cliente</th>
            {products.map((product) => (
              <th key={product.key} className="px-2 py-2 text-right">{product.label}</th>
            ))}
            <th className="px-2 py-2 text-right">Peso</th>
            <th className="px-2 py-2 text-right">Importe</th>
            <th className="px-2 py-2">Lugar de entrega</th>
          </tr>
        </thead>
        <tbody>
          {trip.orders.map((order) => (
            <tr key={order.id} className="border-t border-line">
              <td className="px-2 py-2 font-mono font-bold text-ink">{order.folio}</td>
              <td className="max-w-56 truncate px-2 py-2 font-semibold text-slate-800">{order.customer_name_snapshot || "Sin cliente"}</td>
              {products.map((product) => (
                <td key={product.key} className="px-2 py-2 text-right text-slate-700">{productQty(order, product.key)}</td>
              ))}
              <td className="px-2 py-2 text-right text-slate-600">{number.format(order.peso_kg || 0)} kg</td>
              <td className="px-2 py-2 text-right font-semibold text-ink">{money.format(order.importe || 0)}</td>
              <td className="max-w-72 px-2 py-2 text-slate-700">{order.delivery_address || order.city || "Sin lugar"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function vehicleName(vehicles: CatalogRow[], id?: string | null) {
  return vehicles.find((row) => row.id === id)?.nombre || "";
}

function vehicleColorStyle(index: number): CSSProperties {
  const colors = [
    { borderColor: "#7aa6b8", backgroundColor: "#edf6f8" },
    { borderColor: "#c6a46b", backgroundColor: "#fbf6eb" },
    { borderColor: "#91b58a", backgroundColor: "#f1f8ef" },
    { borderColor: "#b890a8", backgroundColor: "#faf0f5" },
    { borderColor: "#9e9ac8", backgroundColor: "#f3f2fa" },
    { borderColor: "#c6907c", backgroundColor: "#fbf1ed" }
  ];
  return colors[index % colors.length];
}

function productKey(item: NonNullable<OrderRow["items"]>[number]) {
  return String(item.inventory_product_id || item.product_id || item.product_name_snapshot || item.description || "producto");
}

function productLabel(item: NonNullable<OrderRow["items"]>[number]) {
  return String(item.product_name_snapshot || item.description || "Producto");
}

function topTripProducts(trip: TripRow, limit: number) {
  const totals = new Map<string, { key: string; label: string; quantity: number }>();
  for (const order of trip.orders) {
    for (const item of order.items || []) {
      const key = productKey(item);
      const current = totals.get(key) || { key, label: productLabel(item), quantity: 0 };
      current.quantity += Number(item.quantity || 0);
      totals.set(key, current);
    }
  }
  return Array.from(totals.values()).sort((a, b) => b.quantity - a.quantity || a.label.localeCompare(b.label)).slice(0, limit);
}

function productQty(order: OrderRow, key: string) {
  let quantity = 0;
  let unit = "";
  for (const item of order.items || []) {
    if (productKey(item) !== key) continue;
    quantity += Number(item.quantity || 0);
    unit = String(item.unit || unit || "");
  }
  return quantity ? `${number.format(quantity)} ${unit}` : "-";
}

async function openRemisionPdf(companyId: string, folio: string, hidePrices: boolean) {
  const res = await fetch(`/api/logistics/remision-pdf?company_id=${encodeURIComponent(companyId)}&folio=${encodeURIComponent(folio)}&hide_prices=${hidePrices ? "true" : "false"}`, { credentials: "same-origin" });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || !json.ok || !json.data?.html) return;
  openHtmlDocument(json.data.html);
}

function openLogisticsDayPdf(day: string, trips: TripRow[], catalogs: LogisticsData["catalogs"]) {
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Logistica ${escapeHtml(day)}</title><style>
    body{font-family:Arial,sans-serif;color:#172033;margin:20px;font-size:12px}
    h1{font-size:20px;margin:0 0 14px}
    h2{font-size:15px;margin:18px 0 6px}
    section{break-inside:avoid;margin:0 0 14px;padding:10px;border-left:8px solid #7aa6b8;border-radius:4px;background:#edf6f8}
    section:nth-of-type(6n+2){border-left-color:#c6a46b;background:#fbf6eb}
    section:nth-of-type(6n+3){border-left-color:#91b58a;background:#f1f8ef}
    section:nth-of-type(6n+4){border-left-color:#b890a8;background:#faf0f5}
    section:nth-of-type(6n+5){border-left-color:#9e9ac8;background:#f3f2fa}
    section:nth-of-type(6n+6){border-left-color:#c6907c;background:#fbf1ed}
    table{width:100%;border-collapse:collapse;margin-top:6px}
    th,td{border:1px solid #d8dee8;padding:5px;text-align:left;vertical-align:top}
    th{background:#f3f6f9;font-size:10px;text-transform:uppercase}
    .muted{color:#667085}
  </style></head><body><h1>Logistica ${escapeHtml(day)}</h1>${trips.map((trip) => `<section><h2>${escapeHtml(trip.hora_inicio?.slice(0, 5) || "--:--")} - ${escapeHtml(trip.folio)} · ${escapeHtml(vehicleName(catalogs.vehicles, trip.vehiculo_id) || "Sin vehiculo")}</h2><p class="muted">${trip.summary.orders_count} pedidos · ${number.format(trip.summary.peso_total_kg)} kg · ${money.format(trip.summary.importe_total)}</p>${printableTripTable(trip)}</section>`).join("")}<script>window.print()</script></body></html>`;
  openHtmlDocument(html);
}

function printableTripTable(trip: TripRow) {
  const products = topTripProducts(trip, 8);
  return `<table><thead><tr><th>Pedido</th><th>Cliente</th>${products.map((product) => `<th>${escapeHtml(product.label)}</th>`).join("")}<th>Peso</th><th>Importe</th><th>Lugar de entrega</th></tr></thead><tbody>${trip.orders.map((order) => `<tr><td>${escapeHtml(order.folio)}</td><td>${escapeHtml(order.customer_name_snapshot || "Sin cliente")}</td>${products.map((product) => `<td>${escapeHtml(productQty(order, product.key))}</td>`).join("")}<td>${number.format(order.peso_kg || 0)} kg</td><td>${money.format(order.importe || 0)}</td><td>${escapeHtml(order.delivery_address || order.city || "Sin lugar")}</td></tr>`).join("")}</tbody></table>${printableProductTotals(trip)}`;
}

function printableProductTotals(trip: TripRow) {
  const totals = trip.summary.product_totals || [];
  if (!totals.length) return "";
  return `<div style="margin-top:8px"><h3 style="font-size:12px;margin:0 0 4px">Totales por producto</h3><table style="max-width:620px"><thead><tr><th>Producto</th><th>Cantidad</th><th>Peso</th><th>Importe</th></tr></thead><tbody>${totals.map((product) => `<tr><td>${escapeHtml(product.product_name)}</td><td>${number.format(product.quantity)} ${escapeHtml(product.unit || "")}</td><td>${number.format(product.weight_kg_total || 0)} kg</td><td>${money.format(product.line_total || 0)}</td></tr>`).join("")}</tbody></table></div>`;
}

function openHtmlDocument(html: string) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank");
  if (!win) {
    URL.revokeObjectURL(url);
    return;
  }
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char] || char));
}

function ConfigTab({ catalogs, action, busy }: { catalogs: LogisticsData["catalogs"]; action: (name: string, context: Record<string, unknown>) => Promise<boolean>; busy: string }) {
  const [vehicle, setVehicle] = useState("");
  const [vehiclePlate, setVehiclePlate] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [vehicleCapacity, setVehicleCapacity] = useState("");
  const [driver, setDriver] = useState("");
  const [driverPhone, setDriverPhone] = useState("");
  return (
    <div className="grid gap-4">
      <section className="border border-line bg-white p-3">
        <h2 className="text-lg font-semibold">Vehiculos</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(180px,1fr)_120px_120px_120px_44px]">
          <input value={vehicle} onChange={(event) => setVehicle(event.target.value)} className="input" placeholder="Nombre" />
          <input value={vehiclePlate} onChange={(event) => setVehiclePlate(event.target.value)} className="input" placeholder="Placa" />
          <input value={vehicleType} onChange={(event) => setVehicleType(event.target.value)} className="input" placeholder="Tipo" />
          <input value={vehicleCapacity} onChange={(event) => setVehicleCapacity(event.target.value)} type="number" min="0" step="0.01" className="input" placeholder="Kg max" />
          <button disabled={!vehicle || Boolean(busy)} onClick={async () => { if (await action("catalog_manage", { action: "create", catalog: "vehicle", nombre: vehicle, placa: vehiclePlate || null, tipo: vehicleType || null, capacidad_peso_kg: vehicleCapacity ? Number(vehicleCapacity) : null })) { setVehicle(""); setVehiclePlate(""); setVehicleType(""); setVehicleCapacity(""); } }} className="btn-primary h-10 w-11 justify-center px-0" title="Agregar vehiculo" aria-label="Agregar vehiculo">
            <Plus size={16} />
          </button>
        </div>
        <CatalogEditor catalog="vehicle" rows={catalogs.vehicles} action={action} busy={busy} />
      </section>
      <section className="border border-line bg-white p-3">
        <h2 className="text-lg font-semibold">Choferes</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(180px,1fr)_170px_44px]">
          <input value={driver} onChange={(event) => setDriver(event.target.value)} className="input" placeholder="Nombre" />
          <input value={driverPhone} onChange={(event) => setDriverPhone(event.target.value)} className="input" placeholder="Telefono" />
          <button disabled={!driver || Boolean(busy)} onClick={async () => { if (await action("catalog_manage", { action: "create", catalog: "driver", nombre: driver, telefono: driverPhone || null })) { setDriver(""); setDriverPhone(""); } }} className="btn-primary h-10 w-11 justify-center px-0" title="Agregar chofer" aria-label="Agregar chofer">
            <Plus size={16} />
          </button>
        </div>
        <CatalogEditor catalog="driver" rows={catalogs.drivers} action={action} busy={busy} />
      </section>
      <section className="border border-line bg-white p-3">
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

function CatalogEditor({ catalog, rows, action, busy }: { catalog: "vehicle" | "driver"; rows: CatalogRow[]; action: (name: string, context: Record<string, unknown>) => Promise<boolean>; busy: string }) {
  return (
    <div className="mt-3 grid gap-2">
      {rows.map((row) => (
        <CatalogEditorRow key={row.id} catalog={catalog} row={row} action={action} busy={busy} />
      ))}
      {!rows.length && <p className="border border-line px-3 py-2 text-sm text-slate-500">Sin registros</p>}
    </div>
  );
}

function CatalogEditorRow({ catalog, row, action, busy }: { catalog: "vehicle" | "driver"; row: CatalogRow; action: (name: string, context: Record<string, unknown>) => Promise<boolean>; busy: string }) {
  const [nombre, setNombre] = useState(row.nombre || "");
  const [tipo, setTipo] = useState(row.tipo || "");
  const [placa, setPlaca] = useState(row.placa || "");
  const [telefono, setTelefono] = useState(row.telefono || "");
  const [capacidad, setCapacidad] = useState(row.capacidad_peso_kg == null ? "" : String(row.capacidad_peso_kg));
  const [activo, setActivo] = useState(row.activo !== false);
  const [status, setStatus] = useState(row.status || (catalog === "vehicle" ? "disponible" : "activo"));

  async function save() {
    await action("catalog_manage", {
      action: "update",
      catalog,
      id: row.id,
      nombre,
      ...(catalog === "vehicle" ? { tipo: tipo || null, placa: placa || null, capacidad_peso_kg: capacidad === "" ? null : Number(capacidad), status, activo } : { telefono: telefono || null, status, activo })
    });
  }

  return (
    <div className="border border-line bg-slate-50 p-3">
      <div className="grid gap-2">
        <div className="grid grid-cols-[minmax(0,1fr)_44px] gap-2">
          <input value={nombre} onChange={(event) => setNombre(event.target.value)} className="input min-h-10 font-semibold" placeholder="Nombre" />
          <button onClick={save} disabled={!nombre || Boolean(busy)} className="btn-soft h-10 w-11 justify-center px-0" title="Guardar cambios" aria-label="Guardar cambios">
            <Save size={16} />
          </button>
        </div>
        {catalog === "vehicle" ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-[140px_140px_140px_180px_110px]">
            <input value={placa} onChange={(event) => setPlaca(event.target.value)} className="input h-9" placeholder="Placa" />
            <input value={tipo} onChange={(event) => setTipo(event.target.value)} className="input h-9" placeholder="Tipo" />
            <input value={capacidad} onChange={(event) => setCapacidad(event.target.value)} type="number" min="0" step="0.01" className="input h-9" placeholder="Kg max" />
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="input h-9">
              <option value="disponible">Disponible</option>
              <option value="en_ruta">En ruta</option>
              <option value="mantenimiento">Mantenimiento</option>
              <option value="inactivo">Inactivo</option>
            </select>
            <label className="flex min-h-9 items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={activo} onChange={(event) => setActivo(event.target.checked)} />
              Activo
            </label>
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-[minmax(180px,1fr)_150px_110px]">
            <input value={telefono} onChange={(event) => setTelefono(event.target.value)} className="input h-9" placeholder="Telefono" />
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="input h-9">
              <option value="activo">Activo</option>
              <option value="inactivo">Inactivo</option>
            </select>
            <label className="flex min-h-9 items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={activo} onChange={(event) => setActivo(event.target.checked)} />
              Activo
            </label>
          </div>
        )}
      </div>
    </div>
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

function tripScheduleLabel(assignment: NonNullable<OrderRow["logistics_assignment"]>) {
  const start = assignment.hora_inicio ? String(assignment.hora_inicio).slice(0, 5) : "";
  const end = assignment.hora_fin ? String(assignment.hora_fin).slice(0, 5) : "";
  if (start && end) return `${start}-${end}`;
  return start || "Sin hora";
}
