-- Atomic increment so concurrent paid orders using the same code can't race
-- past usage_limit (the checkout pricing check in lib/pricing.ts still runs
-- first, this just keeps the counter itself correct under concurrency).
create function increment_promo_usage(promo_code_input text) returns void
  language sql security definer
  set search_path = public
as $$
  update promo_codes set times_used = times_used + 1 where code = promo_code_input;
$$;

revoke all on function increment_promo_usage(text) from public;
grant execute on function increment_promo_usage(text) to service_role;
