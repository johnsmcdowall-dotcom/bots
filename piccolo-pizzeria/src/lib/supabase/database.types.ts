// Hand-maintained types mirroring `supabase/migrations/*.sql`. Once the
// project is linked to a real Supabase instance, these can be regenerated
// authoritatively with:
//   npx supabase gen types typescript --linked > src/lib/supabase/database.types.ts
//
// NOTE: the Supabase clients in `lib/supabase/{server,browser,admin}.ts` are
// deliberately NOT parameterised with `Database` here. The installed
// @supabase/supabase-js's select-query-parser has a reproducible bug where
// a second typed `.select("*")` call in the same file resolves to `never`
// (confirmed via isolated repro — a single query in a file is fine, a
// second one in the same file breaks both). Every file under `lib/data/`
// makes several such calls, so instead the clients are used untyped and
// each query's `data` is cast to the matching `*Row` type below, which is
// still kept in lockstep with the migrations for that purpose.

export interface Json {
  [key: string]: string | number | boolean | null | Json | Json[];
}

export interface BusinessSettingsRow {
  id: number;
  name: string;
  tagline: string;
  phone: string;
  email: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  postcode: string;
  latitude: number;
  longitude: number;
  instagram_url: string | null;
  facebook_url: string | null;
  tiktok_url: string | null;
  ordering_paused: boolean;
  ordering_paused_message: string | null;
  announcement_active: boolean;
  announcement_message: string | null;
  rewards_enabled: boolean;
  asap_orders_enabled: boolean;
  scheduled_orders_enabled: boolean;
  delivery_enabled: boolean;
  current_wait_minutes: number;
  min_prep_minutes: number;
  max_advance_order_days: number;
  slot_interval_minutes: number;
  orders_per_slot: number;
  delivery_orders_per_slot: number;
  updated_at: string;
}

export interface OpeningHoursRow {
  id: string;
  day_of_week: number;
  is_open: boolean;
  open_time: string;
  close_time: string;
}

export interface SpecialHoursRow {
  id: string;
  date: string;
  label: string;
  is_open: boolean;
  open_time: string | null;
  close_time: string | null;
  created_at: string;
}

export interface CategoryRow {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  sort_order: number;
  created_at: string;
}

export interface ModifierGroupRow {
  id: string;
  name: string;
  description: string | null;
  required: boolean;
  min_select: number;
  max_select: number;
  sort_order: number;
}

export interface ModifierRow {
  id: string;
  group_id: string;
  name: string;
  price_minor: number;
  sold_out: boolean;
  is_default: boolean;
  sort_order: number;
}

export interface ProductRow {
  id: string;
  category_id: string;
  slug: string;
  name: string;
  description: string | null;
  price_minor: number;
  image_url: string | null;
  dietary: string[];
  allergens: string[];
  sold_out: boolean;
  featured: boolean;
  popular: boolean;
  is_new: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  stock_limited: boolean;
  stock_remaining: number | null;
}

export interface ProductModifierGroupRow {
  product_id: string;
  modifier_group_id: string;
}

export interface UpsellRuleRow {
  id: string;
  trigger_type: "product" | "category";
  trigger_product_id: string | null;
  trigger_category_id: string | null;
  suggested_product_id: string;
  sort_order: number;
}

export interface DeliveryZoneRow {
  id: string;
  postcode_prefixes: string[];
  fee_minor: number;
  min_order_minor: number;
  free_delivery_threshold_minor: number | null;
  estimated_minutes: number;
}

export interface PromoCodeRow {
  id: string;
  code: string;
  type: "percentage" | "fixed";
  value: number;
  min_basket_minor: number;
  starts_at: string | null;
  ends_at: string | null;
  usage_limit: number | null;
  times_used: number;
  active: boolean;
  created_at: string;
}

export interface CustomerRow {
  id: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  email: string | null;
  created_at: string;
}

export interface AddressRow {
  id: string;
  customer_id: string;
  label: string | null;
  line1: string;
  line2: string | null;
  postcode: string;
  is_default: boolean;
}

export interface OrderRow {
  id: string;
  order_number: string;
  status: string;
  method: string;
  timing: string;
  requested_time: string;
  customer_first_name: string;
  customer_last_name: string;
  customer_phone: string;
  customer_email: string;
  address_line1: string | null;
  address_line2: string | null;
  address_postcode: string | null;
  notes: string | null;
  subtotal_minor: number;
  delivery_fee_minor: number;
  discount_minor: number;
  total_minor: number;
  promo_code: string | null;
  payment_status: string;
  stripe_payment_intent_id: string | null;
  customer_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderItemRow {
  id: string;
  order_id: string;
  product_id: string | null;
  name: string;
  unit_price_minor: number;
  quantity: number;
  line_total_minor: number;
  notes: string | null;
}

export interface OrderItemModifierRow {
  id: string;
  order_item_id: string;
  group_id: string | null;
  option_id: string | null;
  group_name: string;
  option_name: string;
  price_minor: number;
}

export interface OrderStatusHistoryRow {
  id: string;
  order_id: string;
  status: string;
  changed_at: string;
  changed_by: string | null;
}

export interface ProfileRow {
  id: string;
  role: "admin" | "staff";
  full_name: string | null;
  created_at: string;
}

export interface WebhookEventRow {
  id: string;
  type: string;
  processed_at: string;
}

type TableDef<Row> = { Row: Row; Insert: Partial<Row>; Update: Partial<Row>; Relationships: [] };

export interface Database {
  public: {
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Tables: {
      business_settings: TableDef<BusinessSettingsRow>;
      opening_hours: TableDef<OpeningHoursRow>;
      special_hours: TableDef<SpecialHoursRow>;
      categories: TableDef<CategoryRow>;
      modifier_groups: TableDef<ModifierGroupRow>;
      modifiers: TableDef<ModifierRow>;
      products: TableDef<ProductRow>;
      product_modifier_groups: TableDef<ProductModifierGroupRow>;
      upsell_rules: TableDef<UpsellRuleRow>;
      delivery_zones: TableDef<DeliveryZoneRow>;
      promo_codes: TableDef<PromoCodeRow>;
      customers: TableDef<CustomerRow>;
      addresses: TableDef<AddressRow>;
      orders: TableDef<OrderRow>;
      order_items: TableDef<OrderItemRow>;
      order_item_modifiers: TableDef<OrderItemModifierRow>;
      order_status_history: TableDef<OrderStatusHistoryRow>;
      profiles: TableDef<ProfileRow>;
      webhook_events: TableDef<WebhookEventRow>;
    };
  };
}
