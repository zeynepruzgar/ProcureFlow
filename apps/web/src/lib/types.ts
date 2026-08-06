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
