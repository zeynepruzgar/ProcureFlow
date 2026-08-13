// Backend API'sinin dondurdugu veri sekilleri (Pydantic semalariyla ayni).

export interface Product {
  id: string;
  sku: string;
  name: string;
  unit: string;
  min_stock_level: number;
  reorder_qty: number;
  preferred_supplier_id: string | null;
  created_at?: string | null;
}

export interface Supplier {
  id: string;
  name: string;
  contact_email: string | null;
  lead_time_days: number;
  is_active: boolean;
  created_at?: string | null;
}

export interface StockLevel {
  id: string;
  product_id: string;
  location: string;
  quantity: number;
  updated_at?: string | null;
  product?: {
    name?: string;
    sku?: string;
    min_stock_level?: number;
    unit?: string;
  } | null;
}

export interface OrderLine {
  id: string;
  product_id: string;
  qty: number;
  unit_price: number;
  product?: { name?: string; sku?: string } | null;
}

export interface Order {
  id: string;
  supplier_id: string;
  status: string;
  expected_delivery_date: string | null;
  created_at?: string | null;
  supplier?: { name?: string } | null;
  lines?: OrderLine[] | null;
}

export type SignalType = "low_stock" | "delayed_order" | "price_spike";
export type Severity = "low" | "medium" | "high";

export interface Signal {
  id: string;
  type: SignalType;
  entity_id: string;
  severity: Severity;
  status: "open" | "handled";
  detected_at?: string | null;
}

export interface ScanResult {
  created: number;
  updated: number;
  closed: number;
  open_signals: Signal[];
}

export type RecommendationStatus = "pending" | "approved" | "rejected";

export interface Recommendation {
  id: string;
  signal_id: string;
  agent_run_id: string | null;
  rationale: string | null;
  suggested_supplier_id: string | null;
  suggested_qty: number | null;
  status: RecommendationStatus;
  reviewer_id: string | null;
  created_at?: string | null;
}
