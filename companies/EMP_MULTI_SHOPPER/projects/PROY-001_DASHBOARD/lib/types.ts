export type StatusTone = "green" | "yellow" | "red" | "blue" | "slate";

export type SalesQuote = {
  id: string;
  folio?: string;
  customer_name: string;
  project_name?: string | null;
  quote_date?: string | null;
  status: string;
  total_items?: number;
  updated_at?: string | null;
};

export type Product = {
  id: string;
  folio?: string;
  canonical_name: string;
  category_name?: string | null;
  unit?: string | null;
  brand?: string | null;
  status?: string;
  erp_product_id?: string | null;
};

export type Supplier = {
  id: string;
  folio?: string;
  name: string;
  city?: string | null;
  state?: string | null;
  supplier_type?: string | null;
  categories?: string[];
  status?: string;
};

export type PurchaseQuote = {
  id: string;
  folio?: string;
  supplier_name?: string | null;
  sales_quote_folio?: string | null;
  channel?: string | null;
  status: string;
  created_at?: string | null;
};

export type DocumentRow = {
  id: string;
  folio?: string;
  file_name: string;
  file_type?: string | null;
  document_type?: string | null;
  processing_status?: string | null;
  created_at?: string | null;
};

export type PriceHistory = {
  id: string;
  product_name?: string | null;
  supplier_name?: string | null;
  unit_price?: number | null;
  currency?: string | null;
  price_date?: string | null;
};

export type DashboardData = {
  kpis: {
    active_sales_quotes: number;
    products: number;
    suppliers: number;
    purchase_quotes: number;
    documents: number;
    price_records: number;
  };
  sales_quotes: SalesQuote[];
  products: Product[];
  suppliers: Supplier[];
  purchase_quotes: PurchaseQuote[];
  documents: DocumentRow[];
  price_history: PriceHistory[];
};

export const emptyDashboardData: DashboardData = {
  kpis: {
    active_sales_quotes: 0,
    products: 0,
    suppliers: 0,
    purchase_quotes: 0,
    documents: 0,
    price_records: 0,
  },
  sales_quotes: [],
  products: [],
  suppliers: [],
  purchase_quotes: [],
  documents: [],
  price_history: [],
};
