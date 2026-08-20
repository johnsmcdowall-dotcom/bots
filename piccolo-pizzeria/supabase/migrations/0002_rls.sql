-- Row Level Security
--
-- Public menu/business data is readable by anyone (anon + authenticated) so
-- the storefront works for guests. Writes to that data require an
-- authenticated admin (profiles.role = 'admin'), via is_admin().
--
-- Orders, order line items, promo codes and webhook events have NO public
-- policies at all — every read/write against them goes through server-only
-- code using the service-role client (lib/supabase/admin.ts), which bypasses
-- RLS entirely. This keeps guest checkout simple (no customer auth required)
-- while making sure a browser can never read someone else's order or enumerate
-- promo codes.

-- ---------------------------------------------------------------------------
-- Table-level grants
--
-- RLS policies only ever narrow what a role can already see per the grant
-- system underneath — they don't grant access themselves. Supabase projects
-- provision these automatically for anon/authenticated, but they're spelled
-- out here so the schema is correct and portable on any Postgres instance
-- (self-hosted Supabase, a local `supabase start`, or a plain Postgres box).
-- ---------------------------------------------------------------------------
grant usage on schema public to anon, authenticated, service_role;

grant select on
  business_settings, opening_hours, special_hours,
  categories, modifier_groups, modifiers, products, product_modifier_groups,
  delivery_zones
  to anon, authenticated;

grant insert, update, delete on
  business_settings, opening_hours, special_hours,
  categories, modifier_groups, modifiers, products, product_modifier_groups,
  delivery_zones, promo_codes, profiles
  to authenticated;
grant select on promo_codes to authenticated;

grant select, insert, update on customers, addresses to authenticated;
grant select, update on profiles to authenticated;

grant select, update on orders to authenticated;
grant select on order_items, order_item_modifiers, order_status_history to authenticated;
grant insert on order_status_history to authenticated;

alter table profiles enable row level security;
alter table business_settings enable row level security;
alter table opening_hours enable row level security;
alter table special_hours enable row level security;
alter table categories enable row level security;
alter table modifier_groups enable row level security;
alter table modifiers enable row level security;
alter table products enable row level security;
alter table product_modifier_groups enable row level security;
alter table delivery_zones enable row level security;
alter table promo_codes enable row level security;
alter table customers enable row level security;
alter table addresses enable row level security;
alter table orders enable row level security;
alter table order_items enable row level security;
alter table order_item_modifiers enable row level security;
alter table order_status_history enable row level security;
alter table webhook_events enable row level security;

-- profiles: a user can read their own profile (used to check admin status
-- client-side); only admins can manage staff records.
create policy "profiles_select_own" on profiles for select
  using (auth.uid() = id or is_admin());
create policy "profiles_admin_write" on profiles for all
  using (is_admin()) with check (is_admin());

-- Public read, admin write, for all storefront/menu data.
create policy "business_settings_public_read" on business_settings for select using (true);
create policy "business_settings_admin_write" on business_settings for all
  using (is_admin()) with check (is_admin());

create policy "opening_hours_public_read" on opening_hours for select using (true);
create policy "opening_hours_admin_write" on opening_hours for all
  using (is_admin()) with check (is_admin());

create policy "special_hours_public_read" on special_hours for select using (true);
create policy "special_hours_admin_write" on special_hours for all
  using (is_admin()) with check (is_admin());

create policy "categories_public_read" on categories for select using (true);
create policy "categories_admin_write" on categories for all
  using (is_admin()) with check (is_admin());

create policy "modifier_groups_public_read" on modifier_groups for select using (true);
create policy "modifier_groups_admin_write" on modifier_groups for all
  using (is_admin()) with check (is_admin());

create policy "modifiers_public_read" on modifiers for select using (true);
create policy "modifiers_admin_write" on modifiers for all
  using (is_admin()) with check (is_admin());

create policy "products_public_read" on products for select using (true);
create policy "products_admin_write" on products for all
  using (is_admin()) with check (is_admin());

create policy "product_modifier_groups_public_read" on product_modifier_groups for select using (true);
create policy "product_modifier_groups_admin_write" on product_modifier_groups for all
  using (is_admin()) with check (is_admin());

create policy "delivery_zones_public_read" on delivery_zones for select using (true);
create policy "delivery_zones_admin_write" on delivery_zones for all
  using (is_admin()) with check (is_admin());

-- Promo codes: admin-only, even for reads (validated server-side with the
-- service-role client during checkout, never fetched by the browser).
create policy "promo_codes_admin_all" on promo_codes for all
  using (is_admin()) with check (is_admin());

-- Customers can manage their own saved details; staff can view for support.
create policy "customers_own" on customers for select using (auth.uid() = id or is_staff());
create policy "customers_own_write" on customers for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "customers_own_insert" on customers for insert with check (auth.uid() = id);

create policy "addresses_own" on addresses for all
  using (customer_id = auth.uid() or is_staff())
  with check (customer_id = auth.uid());

-- Orders and everything under them: staff (admin/staff) can read and manage
-- via their authenticated session in /admin; guest checkout writes happen
-- through the service-role client server-side, which bypasses RLS.
create policy "orders_staff_read" on orders for select using (is_staff());
create policy "orders_staff_write" on orders for update using (is_staff()) with check (is_staff());

create policy "order_items_staff_read" on order_items for select using (is_staff());
create policy "order_item_modifiers_staff_read" on order_item_modifiers for select using (is_staff());
create policy "order_status_history_staff_read" on order_status_history for select using (is_staff());
create policy "order_status_history_staff_insert" on order_status_history for insert with check (is_staff());

-- webhook_events: no policies — service role only.
