export interface User {
  id: number;
  username: string;
}

export interface SummaryStats {
  total_spend_cents: number;
  receipt_count: number;
  distinct_product_count: number;
  average_basket_cents: number;
  current_month_spend_cents: number;
}

export interface BudgetStatus {
  month: string;
  budget_cents: number;
  spent_cents: number;
  remaining_cents: number;
}

export interface BudgetSettingUpdate {
  monthly_budget_cents: number;
}

export interface BudgetSettingOut {
  monthly_budget_cents: number;
}

export interface SpendingBucket {
  period: string;
  total_cents: number;
}

export type SpendingGranularity = "week" | "month";

export interface SpendingOverTime {
  granularity: SpendingGranularity;
  buckets: SpendingBucket[];
}

export interface TopItem {
  product_id: number;
  product_name: string;
  total_quantity: number;
  total_spend_cents: number;
}

export interface PriceTrendPoint {
  date: string;
  unit_price_cents: number;
  quantity: number;
}

export interface PriceTrend {
  product_id: number;
  product_name: string;
  points: PriceTrendPoint[];
  min_price_cents: number;
  max_price_cents: number;
  avg_price_cents: number;
}

export interface ProductOut {
  id: number;
  name: string;
  purchase_count: number;
  category_key: CategoryKey | null;
}

export type CategoryKey =
  | "fruit"
  | "vegetables"
  | "dairy"
  | "bakery"
  | "meat"
  | "fish"
  | "frozen"
  | "ready_meals"
  | "beverages"
  | "pantry"
  | "sweets"
  | "personal_care"
  | "household"
  | "other";

export interface Category {
  key: CategoryKey;
  label: string;
}

export interface CategorySpending {
  category_key: CategoryKey | null;
  total_cents: number;
}

export interface ProductCategoryUpdate {
  category_key: CategoryKey;
}

export interface ReceiptSummary {
  id: number;
  received_date: string;
  effective_date: string;
  from_address: string;
  item_count: number;
  total_cents: number;
}

export interface PaginatedReceipts {
  items: ReceiptSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReceiptItemOut {
  product_name: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
  order_number: string | null;
}

export interface ReceiptDetail {
  id: number;
  received_date: string;
  effective_date: string;
  from_address: string;
  items: ReceiptItemOut[];
  total_cents: number;
}

export type PriceHistoryRange = "3m" | "6m" | "12m" | "all";
