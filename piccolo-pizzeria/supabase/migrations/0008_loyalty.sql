-- Stage 9: loyalty/rewards architecture only — schema and a server-side
-- earning hook, no customer-facing surface of any kind. rewards_enabled
-- defaults false; even once an admin turns it on, nothing changes for a
-- customer except points quietly accruing in the ledger below.
--
-- There are no customer accounts in this app (Order Again works off
-- localStorage + order ids, not login — see Stage 3), so an account here is
-- keyed by the email a customer types at checkout rather than a user id.
-- That's a deliberate, minimal choice for "architecture only": it's enough
-- to prove points can be earned and tracked per customer without inventing
-- an auth system this stage was never asked to build.
create table loyalty_accounts (
  id uuid primary key default gen_random_uuid(),
  customer_email text not null unique,
  customer_phone text,
  points_balance int not null default 0 check (points_balance >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Immutable ledger: every balance change is a row here, never an update or
-- delete — same shape as order_status_history's append-only history. The
-- account's points_balance is a maintained cache of this ledger's sum, kept
-- in sync by award_loyalty_points() below rather than recomputed on every
-- read.
create table loyalty_transactions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references loyalty_accounts(id) on delete cascade,
  order_id uuid references orders(id) on delete set null,
  type text not null check (type in ('earn', 'redeem', 'adjustment')),
  points int not null,
  description text,
  created_at timestamptz not null default now()
);
create index loyalty_transactions_account_id_idx on loyalty_transactions(account_id);

alter table loyalty_accounts enable row level security;
alter table loyalty_transactions enable row level security;
-- No policies on either table — same as webhook_events. This is
-- backend-only bookkeeping with no staff or customer UI, so there is no
-- legitimate reason for the browser (even an authenticated admin) to query
-- these directly; only the service-role admin client can.

-- Atomic earn: appends the ledger row and updates the cached balance in one
-- transaction, mirroring decrement_product_stock's precedent for
-- concurrency-safe balance mutations rather than a read-then-write from
-- application code.
create function award_loyalty_points(
  customer_email_input text,
  customer_phone_input text,
  order_id_input uuid,
  points_input int,
  description_input text
) returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  target_account_id uuid;
begin
  insert into loyalty_accounts (customer_email, customer_phone)
  values (lower(customer_email_input), customer_phone_input)
  on conflict (customer_email) do update set customer_phone = coalesce(excluded.customer_phone, loyalty_accounts.customer_phone)
  returning id into target_account_id;

  insert into loyalty_transactions (account_id, order_id, type, points, description)
  values (target_account_id, order_id_input, 'earn', points_input, description_input);

  update loyalty_accounts
  set points_balance = points_balance + points_input, updated_at = now()
  where id = target_account_id;
end;
$$;

revoke all on function award_loyalty_points(text, text, uuid, int, text) from public;
grant execute on function award_loyalty_points(text, text, uuid, int, text) to service_role;

alter table business_settings add column rewards_enabled boolean not null default false;
comment on column business_settings.rewards_enabled is 'Kill switch for the loyalty ledger. No UI reads this anywhere — flipping it only changes whether markOrderPaid() calls award_loyalty_points().';
