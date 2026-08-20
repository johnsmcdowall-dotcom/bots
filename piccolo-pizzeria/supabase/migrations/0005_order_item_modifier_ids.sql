-- Stage 3 (Order Again): order_item_modifiers only ever stored the modifier's
-- name/price, never its id — the same gap Stage 1 fixed for order_items.product_id.
-- Without the id, reconstructing a past order can only match a modifier option
-- back to the live catalogue by name, which silently breaks the moment an
-- option is renamed. Group/option ids let the reorder flow tell "still the
-- same option, maybe a new price" apart from "genuinely gone" with certainty.
--
-- Nullable + ON DELETE SET NULL, same as product_id: historical rows before
-- this migration keep group_id/option_id null and are treated by the reorder
-- flow as "can't be matched, dropped with an explanation" rather than an error.
alter table order_item_modifiers
  add column group_id uuid references modifier_groups(id) on delete set null,
  add column option_id uuid references modifiers(id) on delete set null;

comment on column order_item_modifiers.group_id is 'Modifier group at time of order, for reorder revalidation. Null for orders placed before this column existed, or if the group was later deleted.';
comment on column order_item_modifiers.option_id is 'Modifier option at time of order, for reorder revalidation. Null for orders placed before this column existed, or if the option was later deleted.';
