import type { LogisticsData } from "@/lib/logistics";

const itemsA = [
  { id: "i1", document_id: "p1", product_name_snapshot: "Varilla 3/8", description: "Varilla 3/8", quantity: 120, unit: "pzas", line_total: 26400, weight_kg_total: 1120 },
  { id: "i2", document_id: "p1", product_name_snapshot: "Cal", description: "Cal", quantity: 40, unit: "bultos", line_total: 5200, weight_kg_total: 1000 },
  { id: "i3", document_id: "p1", product_name_snapshot: "Cemento", description: "Cemento", quantity: 20, unit: "bultos", line_total: 3600, weight_kg_total: 1000 },
  { id: "i4", document_id: "p1", product_name_snapshot: "Alambre", description: "Alambre", quantity: 8, unit: "rollos", line_total: 1800, weight_kg_total: 96 }
];

const itemsB = [
  { id: "i5", document_id: "p2", product_name_snapshot: "Varilla 1/2", description: "Varilla 1/2", quantity: 80, unit: "pzas", line_total: 24800, weight_kg_total: 1200 },
  { id: "i6", document_id: "p2", product_name_snapshot: "Bron", description: "Bron", quantity: 12, unit: "pzas", line_total: 9600, weight_kg_total: 360 },
  { id: "i7", document_id: "p2", product_name_snapshot: "Cal", description: "Cal", quantity: 25, unit: "bultos", line_total: 3250, weight_kg_total: 625 }
];

const itemsC = [
  { id: "i8", document_id: "p3", product_name_snapshot: "Cal", description: "Cal", quantity: 55, unit: "bultos", line_total: 7150, weight_kg_total: 1375 },
  { id: "i9", document_id: "p3", product_name_snapshot: "Malla", description: "Malla", quantity: 16, unit: "rollos", line_total: 6400, weight_kg_total: 240 }
];

const orderA: any = {
  id: "p1",
  folio: "PED-00124",
  customer_name_snapshot: "Constructora Centro",
  fecha_entrega: "2026-07-22",
  city: "Tuxtla",
  city_quadrant: "Norte",
  peso_kg: 3216,
  importe: 37000,
  partida_1: "Varilla 3/8 120 pzas",
  partida_2: "Cal 40 bultos",
  partida_3: "Cemento 20 bultos",
  otras_partidas: "+1 partidas",
  items: itemsA
};

const orderB: any = {
  id: "p2",
  folio: "PED-00125",
  customer_name_snapshot: "Materiales La Sierra",
  fecha_entrega: "2026-07-22",
  city: "San Cristobal",
  city_quadrant: "Centro",
  peso_kg: 2185,
  importe: 37650,
  partida_1: "Varilla 1/2 80 pzas",
  partida_2: "Bron 12 pzas",
  partida_3: "Cal 25 bultos",
  otras_partidas: "",
  items: itemsB
};

const orderC: any = {
  id: "p3",
  folio: "PED-00126",
  customer_name_snapshot: "Obra Oriente",
  fecha_entrega: "2026-07-23",
  city: "Comitan",
  city_quadrant: "Sur",
  peso_kg: 1615,
  importe: 13550,
  partida_1: "Cal 55 bultos",
  partida_2: "Malla 16 rollos",
  partida_3: "",
  otras_partidas: "",
  items: itemsC
};

export const reviewData: LogisticsData = {
  company_id: "EMP_REVIEW",
  key_products: [
    { key: "varilla_3_8", label: "Varilla 3/8" },
    { key: "varilla_1_2", label: "Varilla 1/2" },
    { key: "bron", label: "Bron" },
    { key: "cal", label: "Cal" }
  ],
  duration_minutes_default: 120,
  catalogs: {
    vehicles: [
      { id: "v1", folio: "VEH-00001", nombre: "Camion 3.5T", placa: "ABC-123", capacidad_peso_kg: 3500 },
      { id: "v2", folio: "VEH-00002", nombre: "Torton", placa: "XYZ-789", capacidad_peso_kg: 9000 }
    ],
    drivers: [
      { id: "d1", folio: "CHO-00001", nombre: "Juan Perez", telefono: "9610000000" },
      { id: "d2", folio: "CHO-00002", nombre: "Carlos Ruiz", telefono: "9611111111" }
    ],
    product_config: [
      { id: "k1", product_key: "varilla_3_8", product_label: "Varilla 3/8", priority: 1 },
      { id: "k2", product_key: "varilla_1_2", product_label: "Varilla 1/2", priority: 2 },
      { id: "k3", product_key: "bron", product_label: "Bron", priority: 3 },
      { id: "k4", product_key: "cal", product_label: "Cal", priority: 4 }
    ]
  },
  available_orders: [orderC],
  trips: [
    {
      id: "t1",
      folio: "VIA-00001",
      estado: "programado",
      fecha_viaje: "2026-07-22",
      hora_inicio: "09:00",
      hora_fin: "11:00",
      duracion_minutos: 120,
      vehiculo_id: "v2",
      driver_id: "d1",
      orders: [orderA, orderB],
      summary: {
        orders_count: 2,
        peso_total_kg: 5401,
        importe_total: 74650,
        key_products: [
          { product_id: "var38", product_name: "Varilla 3/8", quantity: 120, unit: "pzas", weight_kg_total: 1120, line_total: 26400 },
          { product_id: "var12", product_name: "Varilla 1/2", quantity: 80, unit: "pzas", weight_kg_total: 1200, line_total: 24800 },
          { product_id: "cal", product_name: "Cal", quantity: 65, unit: "bultos", weight_kg_total: 1625, line_total: 8450 },
          { product_id: "bron", product_name: "Bron", quantity: 12, unit: "pzas", weight_kg_total: 360, line_total: 9600 }
        ],
        product_totals: [
          { product_id: "var38", product_name: "Varilla 3/8", quantity: 120, unit: "pzas", weight_kg_total: 1120, line_total: 26400 },
          { product_id: "var12", product_name: "Varilla 1/2", quantity: 80, unit: "pzas", weight_kg_total: 1200, line_total: 24800 },
          { product_id: "cal", product_name: "Cal", quantity: 65, unit: "bultos", weight_kg_total: 1625, line_total: 8450 },
          { product_id: "bron", product_name: "Bron", quantity: 12, unit: "pzas", weight_kg_total: 360, line_total: 9600 },
          { product_id: "cemento", product_name: "Cemento", quantity: 20, unit: "bultos", weight_kg_total: 1000, line_total: 3600 }
        ]
      }
    }
  ]
};
