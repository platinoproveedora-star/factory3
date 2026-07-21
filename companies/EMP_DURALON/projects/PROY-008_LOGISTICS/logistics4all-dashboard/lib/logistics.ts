import type { SessionUser } from "@/lib/auth";
import { callFactory } from "@/lib/factory";
import type { AccessGrant } from "@/lib/platform";

export type LogisticsData = {
  company_id: string;
  available_orders: OrderRow[];
  trips: TripRow[];
  catalogs: {
    vehicles: CatalogRow[];
    drivers: CatalogRow[];
    product_config: ProductConfigRow[];
  };
  key_products: { key: string; label: string }[];
  duration_minutes_default: number;
};

export type OrderRow = {
  id: string;
  folio: string;
  external_folio?: string | null;
  customer_name_snapshot?: string | null;
  fecha_entrega?: string | null;
  delivery_address?: string | null;
  city?: string | null;
  city_quadrant?: string | null;
  payment_method?: string | null;
  balance_total?: number | null;
  status?: string | null;
  remision_folio?: string | null;
  remision_id?: string | null;
  peso_kg?: number;
  importe?: number;
  partida_1?: string;
  partida_2?: string;
  partida_3?: string;
  otras_partidas?: string;
  items?: OrderItemRow[];
  logistics_assignment?: {
    trip_id: string;
    trip_folio: string;
    trip_estado: string;
    fecha_viaje?: string | null;
    hora_inicio?: string | null;
    hora_fin?: string | null;
    duracion_minutos?: number | null;
    vehiculo_id?: string | null;
    vehiculo_nombre?: string | null;
    driver_id?: string | null;
    driver_nombre?: string | null;
  } | null;
  trip_order?: {
    id?: string;
    folio?: string;
  };
};

export type OrderItemRow = {
  id?: string;
  folio?: string;
  product_id?: string | null;
  inventory_product_id?: string | null;
  product_folio_snapshot?: string | null;
  product_name_snapshot?: string | null;
  description?: string | null;
  quantity?: number | null;
  unit?: string | null;
  line_total?: number | null;
  weight_kg_total?: number | null;
};

export type TripRow = {
  id: string;
  folio: string;
  estado: string;
  fecha_viaje?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  duracion_minutos?: number;
  vehiculo_id?: string | null;
  driver_id?: string | null;
  orders: OrderRow[];
  summary: {
    orders_count: number;
    peso_total_kg: number;
    importe_total: number;
    key_products: ProductTotal[];
    product_totals: ProductTotal[];
  };
};

export type ProductTotal = {
  product_id: string;
  product_name: string;
  quantity: number;
  unit?: string | null;
  weight_kg_total: number;
  line_total: number;
};

export type CatalogRow = {
  id: string;
  folio: string;
  nombre: string;
  tipo?: string | null;
  placa?: string | null;
  telefono?: string | null;
  capacidad_peso_kg?: number | null;
  status?: string | null;
  activo?: boolean | null;
};

export type ProductConfigRow = {
  id: string;
  product_key: string;
  product_label: string;
  priority: number;
};

export function logisticsContext(user: SessionUser, grants: AccessGrant[], companyId: string) {
  return {
    company_id: companyId,
    project_code: process.env.LOGISTICS_PROJECT_CODE,
    module_code: process.env.LOGISTICS_MODULE_CODE || "logistics",
    schema: process.env.LOGISTICS_SCHEMA,
    sales_schema: process.env.LOGISTICS_SALES_SCHEMA,
    schema_ventas: process.env.LOGISTICS_SALES_SCHEMA,
    inventory_schema: process.env.LOGISTICS_INVENTORY_SCHEMA,
    schema_inventario: process.env.LOGISTICS_INVENTORY_SCHEMA,
    inventory_project_code: process.env.LOGISTICS_INVENTORY_PROJECT_CODE,
    project_inv: process.env.LOGISTICS_INVENTORY_PROJECT_CODE,
    inventory_module_code: process.env.LOGISTICS_INVENTORY_MODULE_CODE,
    module_inv: process.env.LOGISTICS_INVENTORY_MODULE_CODE,
    user_id: user.sub,
    user_role: user.role,
    role: grants.some((grant) => grant.role === "platform_admin") ? "platform_admin" : user.role,
    allowed_company_ids: Array.from(new Set(grants.map((grant) => grant.company_id)))
  };
}

export async function loadLogisticsData(user: SessionUser, grants: AccessGrant[], companyId: string) {
  return callFactory<LogisticsData>(
    "vertical_apps4all_logistics/logistics_dashboard_data",
    logisticsContext(user, grants, companyId),
    "data"
  );
}
