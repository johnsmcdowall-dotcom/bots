-- Server-side checkout idempotency (production audit follow-up). The client
-- now sends a stable per-checkout-attempt key (generated once, persisted
-- alongside the basket, cleared only once an order actually completes) with
-- every /api/checkout/create-intent request. This column plus the partial
-- unique index below is the actual concurrency-safety mechanism: two
-- requests racing with the same key can both attempt to INSERT, but
-- Postgres guarantees only one succeeds — the loser's insert fails with a
-- unique violation, and the application layer (createPendingOrder) catches
-- that and returns the winner's row instead of erroring, so "two
-- simultaneous requests for the same checkout attempt" always resolves to
-- exactly one order, no matter which request the database happens to
-- process first.
--
-- Nullable, not unique-across-all-rows: historical orders (and any future
-- internal/admin-created order that never goes through checkout) have no
-- idempotency key at all, and Postgres unique indexes already treat NULL as
-- "no value to compare" — but a partial index (where idempotency_key is not
-- null) makes that intent explicit rather than relying on the default.
alter table orders add column idempotency_key text;
create unique index orders_idempotency_key_idx on orders(idempotency_key) where idempotency_key is not null;
