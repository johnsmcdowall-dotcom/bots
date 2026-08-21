-- Production readiness audit: the orders_staff_write RLS policy correctly
-- restricts *which rows* an authenticated staff/admin session can update
-- (is_staff()), but Postgres RLS policies don't restrict *which columns* —
-- the blanket `grant ... update on orders to authenticated` from 0002_rls.sql
-- meant a valid staff session using the Supabase client directly (bypassing
-- this app's Server Actions, which only ever send { status }) could in
-- principle rewrite total_minor, payment_status, customer details, or
-- anything else on any order. The app itself never does this — it always
-- goes through updateOrderStatus() via the service-role client — so this
-- doesn't change any real behaviour; it closes the gap for a compromised or
-- misused staff credential, on the one table where a lower-privilege role
-- (staff, not just admin) has legitimate write access at all.
revoke update on orders from authenticated;
grant update (status) on orders to authenticated;
