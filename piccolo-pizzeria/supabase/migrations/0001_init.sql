-- Piccolo Pizzeria — initial schema
-- Money is always stored as integer minor currency units (pence).

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- profiles (admin/staff users, linked 1:1 to auth.users)
-- ---------------------------------------------------------------------------
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'staff' check (role in ('admin', 'staff')),
  full_name text,
  created_at timestamptz not null default now()
);

create function is_admin() returns boolean
  language sql security definer stable
  set search_path = public
as $$
  select exists (select 1 from profiles where id = auth.uid() and role = 'admin');
$$;

create function is_staff() returns boolean
  language sql security definer stable
  set search_path = public
as $$
  select exists (select 1 from profiles where id = auth.uid() and role in ('admin', 'staff'));
$$;

-- ---------------------------------------------------------------------------
-- business_settings (single row, id = 1)
-- ---------------------------------------------------------------------------
create table business_settings (
  id smallint primary key default 1 check (id = 1),
  name text not null default 'Piccolo Pizzeria',
  tagline text not null default '',
  phone text not null default '',
  email text not null default '',
  address_line1 text not null default '',
  address_line2 text,
  city text not null default '',
  postcode text not null default '',
  latitude numeric(9, 6) not null default 0,
  longitude numeric(9, 6) not null default 0,
  instagram_url text,
  facebook_url text,
  tiktok_url text,
  ordering_paused boolean not null default false,
  ordering_paused_message text,
  asap_orders_enabled boolean not null default true,
  scheduled_orders_enabled boolean not null default true,
  delivery_enabled boolean not null default false,
  current_wait_minutes int not null default 20 check (current_wait_minutes >= 0),
  min_prep_minutes int not null default 15 check (min_prep_minutes >= 0),
  max_advance_order_days int not null default 5 check (max_advance_order_days >= 0),
  slot_interval_minutes int not null default 15 check (slot_interval_minutes > 0),
  orders_per_slot int not null default 6 check (orders_per_slot > 0),
  delivery_orders_per_slot int not null default 3 check (delivery_orders_per_slot > 0),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- opening_hours (one row per day of week, 0 = Sunday)
-- ---------------------------------------------------------------------------
create table opening_hours (
  id uuid primary key default gen_random_uuid(),
  day_of_week smallint not null unique check (day_of_week between 0 and 6),
  is_open boolean not null default false,
  open_time time not null default '00:00',
  close_time time not null default '00:00'
);

create table special_hours (
  id uuid primary key default gen_random_uuid(),
  date date not null unique,
  label text not null default '',
  is_open boolean not null default false,
  open_time time,
  close_time time,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Menu: categories, products, modifier groups/options
-- ---------------------------------------------------------------------------
create table categories (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  description text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table modifier_groups (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  required boolean not null default false,
  min_select int not null default 0 check (min_select >= 0),
  max_select int not null default 1 check (max_select >= 1),
  sort_order int not null default 0,
  constraint modifier_group_select_range check (min_select <= max_select)
);

create table modifiers (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references modifier_groups(id) on delete cascade,
  name text not null,
  price_minor int not null default 0 check (price_minor >= 0),
  sold_out boolean not null default false,
  is_default boolean not null default false,
  sort_order int not null default 0
);
create index modifiers_group_id_idx on modifiers(group_id);

create table products (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references categories(id) on delete restrict,
  slug text not null unique,
  name text not null,
  description text,
  price_minor int not null check (price_minor >= 0),
  image_url text,
  dietary text[] not null default '{}',
  allergens text[] not null default '{}',
  sold_out boolean not null default false,
  featured boolean not null default false,
  popular boolean not null default false,
  is_new boolean not null default false,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index products_category_id_idx on products(category_id);

create table product_modifier_groups (
  product_id uuid not null references products(id) on delete cascade,
  modifier_group_id uuid not null references modifier_groups(id) on delete cascade,
  primary key (product_id, modifier_group_id)
);

-- ---------------------------------------------------------------------------
-- Delivery & promotions
-- ---------------------------------------------------------------------------
create table delivery_zones (
  id uuid primary key default gen_random_uuid(),
  postcode_prefixes text[] not null default '{}',
  fee_minor int not null default 0 check (fee_minor >= 0),
  min_order_minor int not null default 0 check (min_order_minor >= 0),
  free_delivery_threshold_minor int check (free_delivery_threshold_minor >= 0),
  estimated_minutes int not null default 30 check (estimated_minutes > 0)
);

create table promo_codes (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  type text not null check (type in ('percentage', 'fixed')),
  value int not null check (value >= 0),
  min_basket_minor int not null default 0 check (min_basket_minor >= 0),
  starts_at timestamptz,
  ends_at timestamptz,
  usage_limit int check (usage_limit >= 0),
  times_used int not null default 0 check (times_used >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint promo_percentage_range check (type <> 'percentage' or value <= 100)
);

-- ---------------------------------------------------------------------------
-- Customers (optional accounts) & saved addresses
-- ---------------------------------------------------------------------------
create table customers (
  id uuid primary key references auth.users(id) on delete cascade,
  first_name text,
  last_name text,
  phone text,
  email text,
  created_at timestamptz not null default now()
);

create table addresses (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  label text,
  line1 text not null,
  line2 text,
  postcode text not null,
  is_default boolean not null default false
);
create index addresses_customer_id_idx on addresses(customer_id);

-- ---------------------------------------------------------------------------
-- Orders
-- ---------------------------------------------------------------------------
create table orders (
  id uuid primary key default gen_random_uuid(),
  order_number text not null unique,
  status text not null default 'pending_payment'
    check (status in ('pending_payment', 'received', 'accepted', 'preparing', 'ready', 'completed', 'cancelled')),
  method text not null check (method in ('collection', 'delivery')),
  timing text not null check (timing in ('asap', 'scheduled')),
  requested_time timestamptz not null,
  customer_first_name text not null,
  customer_last_name text not null,
  customer_phone text not null,
  customer_email text not null,
  address_line1 text,
  address_line2 text,
  address_postcode text,
  notes text,
  subtotal_minor int not null check (subtotal_minor >= 0),
  delivery_fee_minor int not null default 0 check (delivery_fee_minor >= 0),
  discount_minor int not null default 0 check (discount_minor >= 0),
  total_minor int not null check (total_minor >= 0),
  promo_code text,
  payment_status text not null default 'pending' check (payment_status in ('pending', 'paid', 'failed')),
  stripe_payment_intent_id text unique,
  customer_id uuid references customers(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index orders_status_idx on orders(status);
create index orders_requested_time_idx on orders(requested_time);
create index orders_created_at_idx on orders(created_at desc);
create index orders_customer_id_idx on orders(customer_id);

create table order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  name text not null,
  unit_price_minor int not null check (unit_price_minor >= 0),
  quantity int not null check (quantity > 0),
  line_total_minor int not null check (line_total_minor >= 0),
  notes text
);
create index order_items_order_id_idx on order_items(order_id);

create table order_item_modifiers (
  id uuid primary key default gen_random_uuid(),
  order_item_id uuid not null references order_items(id) on delete cascade,
  group_name text not null,
  option_name text not null,
  price_minor int not null default 0
);
create index order_item_modifiers_order_item_id_idx on order_item_modifiers(order_item_id);

create table order_status_history (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  status text not null,
  changed_at timestamptz not null default now(),
  changed_by text
);
create index order_status_history_order_id_idx on order_status_history(order_id);

-- Stripe webhook idempotency ledger
create table webhook_events (
  id text primary key,
  type text not null,
  processed_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------
create function set_updated_at() returns trigger
  language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger products_set_updated_at before update on products
  for each row execute function set_updated_at();

create trigger orders_set_updated_at before update on orders
  for each row execute function set_updated_at();

create trigger business_settings_set_updated_at before update on business_settings
  for each row execute function set_updated_at();
