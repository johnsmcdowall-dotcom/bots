-- Optional limited-quantity stock tracking for products (e.g. weekly
-- specials). Most products stay unlimited (stock_limited = false) and this
-- has zero effect on them — the existing sold_out flag remains the primary,
-- unconditional way to take something off the menu.
--
-- Stock reservation strategy (documented in the app's Stage 2 report too):
-- stock is decremented atomically only when a payment actually succeeds
-- (see decrement_product_stock, called from markOrderPaid), never at order
-- creation. This guarantees a failed or abandoned payment can never
-- consume stock — there's nothing to "release" because nothing was ever
-- held. The trade-off is that this is a check-at-fulfilment model, not a
-- hold/reservation model: it fully prevents stock ever going negative or
-- being double-decremented under concurrent payments (the atomic UPDATE's
-- `where stock_remaining >= qty` guard means only one of two simultaneous
-- final-unit payments can succeed in decrementing), but a true
-- millisecond-simultaneous double payment for the very last unit could in
-- theory both be captured before either decrement lands — an accepted,
-- extremely rare edge case for this business's order volume, resolved
-- operationally (the admin still sees both paid orders and can call one
-- customer) rather than by building a full reservation/expiry system.
alter table products
  add column stock_limited boolean not null default false,
  add column stock_remaining int check (stock_remaining >= 0);

comment on column products.stock_limited is 'When true, stock_remaining is authoritative and decremented on payment success.';
comment on column products.stock_remaining is 'Only meaningful when stock_limited = true. NULL means untracked.';

-- Atomically decrements stock for a paid order line, returning whether it
-- succeeded. Never lets stock go negative or below what's actually
-- available under concurrent calls — the WHERE clause and the UPDATE are
-- one atomic statement, not a separate read-then-write.
create function decrement_product_stock(product_id_input uuid, qty_input int) returns boolean
  language plpgsql security definer
  set search_path = public
as $$
declare
  affected int;
begin
  update products
  set stock_remaining = stock_remaining - qty_input
  where id = product_id_input
    and stock_limited = true
    and stock_remaining >= qty_input;
  get diagnostics affected = row_count;
  return affected > 0;
end;
$$;

revoke all on function decrement_product_stock(uuid, int) from public;
grant execute on function decrement_product_stock(uuid, int) to service_role;

-- Releases stock back — used when a *paid* order with limited-stock items
-- is cancelled after the fact (staff-initiated). Not used for
-- failed/abandoned payments, which never decremented in the first place.
create function increment_product_stock(product_id_input uuid, qty_input int) returns void
  language sql security definer
  set search_path = public
as $$
  update products
  set stock_remaining = stock_remaining + qty_input
  where id = product_id_input and stock_limited = true;
$$;

revoke all on function increment_product_stock(uuid, int) from public;
grant execute on function increment_product_stock(uuid, int) to service_role;
