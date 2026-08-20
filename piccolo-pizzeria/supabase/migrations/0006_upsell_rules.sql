-- Stage 6: admin-configured upsell rules. Deliberately simple/rule-based
-- (no ML, no purchase-history modelling) — an admin picks a trigger (a
-- specific product, or an entire category) and one or more products to
-- suggest whenever the customer's basket matches that trigger.
create table upsell_rules (
  id uuid primary key default gen_random_uuid(),
  trigger_type text not null check (trigger_type in ('product', 'category')),
  trigger_product_id uuid references products(id) on delete cascade,
  trigger_category_id uuid references categories(id) on delete cascade,
  suggested_product_id uuid not null references products(id) on delete cascade,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  constraint upsell_rules_trigger_matches_type check (
    (trigger_type = 'product' and trigger_product_id is not null and trigger_category_id is null) or
    (trigger_type = 'category' and trigger_category_id is not null and trigger_product_id is null)
  )
);
create index upsell_rules_trigger_product_idx on upsell_rules(trigger_product_id);
create index upsell_rules_trigger_category_idx on upsell_rules(trigger_category_id);

alter table upsell_rules enable row level security;

-- Same shape as categories/products: public read (the storefront computes
-- suggestions server-side against the live catalogue), admin write.
create policy "upsell_rules_public_read" on upsell_rules for select using (true);
create policy "upsell_rules_admin_write" on upsell_rules for all
  using (is_admin()) with check (is_admin());
