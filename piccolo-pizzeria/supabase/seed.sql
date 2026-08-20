-- Piccolo Pizzeria — demo seed data
--
-- Mirrors src/lib/seed-data.ts (the real Piccolo menu). Run after the
-- migrations to populate a fresh database with a fully working demo menu.
-- Safe to re-run: it clears the tables it seeds first.
--
--   supabase db reset            (applies migrations, then this file)
--   psql "$DATABASE_URL" -f supabase/seed.sql   (or run manually)

truncate table product_modifier_groups, modifiers, modifier_groups, products, categories,
  delivery_zones, promo_codes, opening_hours, special_hours restart identity cascade;

-- ---------------------------------------------------------------------------
-- Business settings
-- ---------------------------------------------------------------------------
insert into business_settings (
  id, name, tagline, phone, email, address_line1, address_line2, city, postcode,
  latitude, longitude, instagram_url, facebook_url,
  ordering_paused, asap_orders_enabled, scheduled_orders_enabled, delivery_enabled,
  current_wait_minutes, min_prep_minutes, max_advance_order_days,
  slot_interval_minutes, orders_per_slot, delivery_orders_per_slot
) values (
  1, 'Piccolo Pizzeria', 'Wood-fired. Hand-stretched. Piccolo.', '01642 000 000', 'hello@piccolopizzeria.co.uk',
  'Elm Tree Social Club', 'Find our current pitch on Instagram', 'Stockton-on-Tees', 'TS19 0EX',
  54.5642, -1.3188, 'https://instagram.com/piccolo_pizzeria25', 'https://facebook.com/piccolopizzeria',
  false, true, true, false,
  25, 20, 5,
  15, 6, 3
)
on conflict (id) do update set
  name = excluded.name, tagline = excluded.tagline, phone = excluded.phone, email = excluded.email,
  address_line1 = excluded.address_line1, address_line2 = excluded.address_line2, city = excluded.city,
  postcode = excluded.postcode, latitude = excluded.latitude, longitude = excluded.longitude,
  instagram_url = excluded.instagram_url, facebook_url = excluded.facebook_url;

-- ---------------------------------------------------------------------------
-- Opening hours (0 = Sunday) — Mon/Tue closed
-- ---------------------------------------------------------------------------
insert into opening_hours (day_of_week, is_open, open_time, close_time) values
  (0, true, '16:00', '20:30'),
  (1, false, '00:00', '00:00'),
  (2, false, '00:00', '00:00'),
  (3, true, '17:00', '21:00'),
  (4, true, '17:00', '21:00'),
  (5, true, '17:00', '21:30'),
  (6, true, '12:00', '21:30');

-- ---------------------------------------------------------------------------
-- Categories
-- ---------------------------------------------------------------------------
insert into categories (id, slug, name, description, sort_order) values
  ('11111111-1111-1111-1111-111111111101', 'pizzas', 'Pizzas', 'Wood-fired in our trailer oven, made to order', 0),
  ('11111111-1111-1111-1111-111111111102', 'specials', 'Pizza Specials', 'Rotating specials — while they last', 1),
  ('11111111-1111-1111-1111-111111111103', 'pizza-sandwiches', 'Pizza Sandwiches', 'Our dough, folded, filled with cheese and baked in the wood oven', 2),
  ('11111111-1111-1111-1111-111111111104', 'dips', 'Dips', null, 3),
  ('11111111-1111-1111-1111-111111111105', 'drinks', 'Drinks', null, 4);

-- ---------------------------------------------------------------------------
-- Modifier groups + options
-- ---------------------------------------------------------------------------
insert into modifier_groups (id, name, description, required, min_select, max_select, sort_order) values
  ('22222222-2222-2222-2222-222222222201', 'Choose Your Base', null, true, 1, 1, 0),
  ('22222222-2222-2222-2222-222222222202', 'Extra Toppings', 'Fired fresh with your pizza', false, 0, 6, 1),
  ('22222222-2222-2222-2222-222222222203', 'Make It Yours', 'Any allergies or intolerances, please contact us before ordering', false, 0, 3, 2),
  ('22222222-2222-2222-2222-222222222204', 'Choose Your Dip', null, false, 0, 2, 3),
  ('22222222-2222-2222-2222-222222222205', 'Optional Extras', null, false, 0, 2, 4);

insert into modifiers (group_id, name, price_minor, sold_out, is_default, sort_order) values
  ('22222222-2222-2222-2222-222222222201', 'Classic Wood-Fired Base', 0, false, true, 0),
  ('22222222-2222-2222-2222-222222222201', 'Gluten Free Base', 250, false, false, 1),

  ('22222222-2222-2222-2222-222222222202', 'Extra Fior di Latte Mozzarella', 150, false, false, 0),
  ('22222222-2222-2222-2222-222222222202', 'Hot Honey Drizzle', 100, false, false, 1),
  ('22222222-2222-2222-2222-222222222202', 'Jalapeños', 100, false, false, 2),
  ('22222222-2222-2222-2222-222222222202', 'Crispy Onions', 100, false, false, 3),
  ('22222222-2222-2222-2222-222222222202', 'Pickled Red Onion', 100, false, false, 4),
  ('22222222-2222-2222-2222-222222222202', 'Extra Chorizo', 200, false, false, 5),

  ('22222222-2222-2222-2222-222222222203', 'No Red Onion', 0, false, false, 0),
  ('22222222-2222-2222-2222-222222222203', 'No Tomato Sauce', 0, false, false, 1),
  ('22222222-2222-2222-2222-222222222203', 'Go Easy on the Cheese', 0, false, false, 2),

  ('22222222-2222-2222-2222-222222222204', 'Garlic Mayo', 100, false, false, 0),
  ('22222222-2222-2222-2222-222222222204', 'Frank''s RedHot Sauce', 100, false, false, 1),

  ('22222222-2222-2222-2222-222222222205', 'Black Pudding', 100, false, false, 0),
  ('22222222-2222-2222-2222-222222222205', 'Hash Browns', 100, false, false, 1);

-- ---------------------------------------------------------------------------
-- Products — Pizzas
-- ---------------------------------------------------------------------------
insert into products (id, category_id, slug, name, description, price_minor, image_url, dietary, allergens, sold_out, featured, popular, is_new, sort_order) values
  ('33333333-3333-3333-3333-333333333301', '11111111-1111-1111-1111-111111111101', 'margherita', 'Margherita', 'A classic, with fresh basil, parmesan & fior di latte mozzarella.', 1000, 'placeholder:pizzas:0', '{vegetarian}', '{gluten,dairy}', false, false, true, false, 0),
  ('33333333-3333-3333-3333-333333333302', '11111111-1111-1111-1111-111111111101', 'pepperoni', 'Pepperoni', 'Everyone''s favourite! Finished with our homemade hot honey.', 1100, 'placeholder:pizzas:1', '{}', '{gluten,dairy}', false, false, true, false, 1),
  ('33333333-3333-3333-3333-333333333303', '11111111-1111-1111-1111-111111111101', 'meat-feast', 'Meat Feast', 'Salami, ham, pepperoni & chorizo.', 1200, 'placeholder:pizzas:0', '{}', '{gluten,dairy}', false, false, false, false, 2),
  ('33333333-3333-3333-3333-333333333304', '11111111-1111-1111-1111-111111111101', 'hawaiian', 'Hawaiian', 'Love it or hate it? Ham & pineapple.', 1100, 'placeholder:pizzas:1', '{}', '{gluten,dairy}', false, false, false, false, 3),
  ('33333333-3333-3333-3333-333333333305', '11111111-1111-1111-1111-111111111101', 'vegetarian', 'Vegetarian', 'Pepper, mushroom, red onion & tomato.', 1000, '/images/real/pizza-vegetarian.jpg', '{vegetarian}', '{gluten,dairy}', false, false, false, false, 4),
  ('33333333-3333-3333-3333-333333333306', '11111111-1111-1111-1111-111111111101', 'pesto', 'Pesto', 'Red onion, tomato, finished with pesto.', 1100, 'placeholder:pizzas:1', '{vegetarian}', '{gluten,dairy,nuts}', false, false, false, false, 5),
  ('33333333-3333-3333-3333-333333333307', '11111111-1111-1111-1111-111111111101', 'chicken-tikka', 'Chicken Tikka', 'Charred pieces of chicken tikka, red onion & jalapeños, drizzled with our house special sauce.', 1200, 'placeholder:pizzas:2', '{spicy}', '{gluten,dairy}', false, false, true, false, 6),
  ('33333333-3333-3333-3333-333333333308', '11111111-1111-1111-1111-111111111101', 'bbq-pulled-pork', 'BBQ Pulled Pork', 'Red onion, BBQ pulled pork & a drizzle of bbq sauce.', 1200, 'placeholder:pizzas:0', '{}', '{gluten,dairy}', false, false, false, false, 7);

-- Specials
insert into products (id, category_id, slug, name, description, price_minor, image_url, dietary, allergens, sold_out, featured, popular, is_new, sort_order) values
  ('33333333-3333-3333-3333-333333333309', '11111111-1111-1111-1111-111111111102', 'buffalo-chicken-feta', 'Buffalo Chicken & Feta', 'Buffalo chicken, feta, finished with spring onion & house made ranch.', 1200, 'placeholder:specials:0', '{spicy}', '{gluten,dairy}', false, true, false, true, 0),
  ('33333333-3333-3333-3333-333333333310', '11111111-1111-1111-1111-111111111102', 'this-weeks-special', 'This Week''s Special', 'A rotating special straight from the wood oven — ask us what''s on today.', 1200, '/images/real/pizza-special-1.jpg', '{}', '{gluten,dairy}', false, true, false, false, 1);

-- Pizza sandwiches
insert into products (id, category_id, slug, name, description, price_minor, image_url, dietary, allergens, sold_out, featured, popular, is_new, sort_order) values
  ('33333333-3333-3333-3333-333333333311', '11111111-1111-1111-1111-111111111103', 'pulled-pork-sandwich', 'Pulled Pork', 'BBQ pulled pork with homemade apple coleslaw, pickled red onion & finished with crispy onions.', 1000, 'placeholder:sides:0', '{}', '{gluten,dairy}', false, false, true, false, 0),
  ('33333333-3333-3333-3333-333333333312', '11111111-1111-1111-1111-111111111103', 'chicken-tikka-sandwich', 'Chicken Tikka', 'Charred chunks of chicken tikka served with Indian style salad, house special sauce & crispy onions.', 1000, 'placeholder:sides:1', '{spicy}', '{gluten,dairy}', false, false, false, false, 1),
  ('33333333-3333-3333-3333-333333333313', '11111111-1111-1111-1111-111111111103', 'mortadella-burrata-sandwich', 'Mortadella & Burrata', 'Italian ham served with fresh burrata, pesto and topped with crushed pistachios.', 1000, 'placeholder:sides:0', '{}', '{gluten,dairy,nuts}', false, true, false, false, 2),
  ('33333333-3333-3333-3333-333333333314', '11111111-1111-1111-1111-111111111103', 'caprese-sandwich', 'Caprese', 'Fresh mozzarella, cherry tomatoes, fresh basil & pesto.', 800, 'placeholder:sides:1', '{vegetarian}', '{gluten,dairy,nuts}', false, false, false, false, 3),
  ('33333333-3333-3333-3333-333333333315', '11111111-1111-1111-1111-111111111103', 'breakfast-sandwich', 'Breakfast Sandwich', 'Bacon, sausage & fried egg.', 800, 'placeholder:sides:0', '{}', '{gluten,dairy,eggs}', false, false, false, false, 4);

-- Dips
insert into products (id, category_id, slug, name, description, price_minor, image_url, dietary, allergens, sold_out, featured, popular, is_new, sort_order) values
  ('33333333-3333-3333-3333-333333333316', '11111111-1111-1111-1111-111111111104', 'garlic-mayo', 'Garlic Mayo', '', 100, 'placeholder:dips:0', '{vegetarian}', '{eggs}', false, false, false, false, 0),
  ('33333333-3333-3333-3333-333333333317', '11111111-1111-1111-1111-111111111104', 'franks-redhot', 'Frank''s RedHot Sauce', '', 100, 'placeholder:dips:0', '{vegan,spicy}', '{}', false, false, false, false, 1);

-- Drinks
insert into products (id, category_id, slug, name, description, price_minor, image_url, dietary, allergens, sold_out, featured, popular, is_new, sort_order) values
  ('33333333-3333-3333-3333-333333333318', '11111111-1111-1111-1111-111111111105', 'coca-cola', 'Coca-Cola', '330ml can', 150, 'placeholder:drinks:0', '{vegan}', '{}', false, false, false, false, 0),
  ('33333333-3333-3333-3333-333333333319', '11111111-1111-1111-1111-111111111105', 'diet-coke', 'Diet Coke', '330ml can', 150, 'placeholder:drinks:1', '{vegan}', '{}', false, false, false, false, 1),
  ('33333333-3333-3333-3333-333333333320', '11111111-1111-1111-1111-111111111105', 'still-water', 'Still Water', '500ml', 120, 'placeholder:drinks:0', '{vegan}', '{}', false, false, false, false, 2);

-- ---------------------------------------------------------------------------
-- Product <-> modifier group links (pizzas + breakfast sandwich)
-- ---------------------------------------------------------------------------
insert into product_modifier_groups (product_id, modifier_group_id)
select p.id, g.id
from products p
cross join lateral (
  values
    ('22222222-2222-2222-2222-222222222201'::uuid),
    ('22222222-2222-2222-2222-222222222202'::uuid),
    ('22222222-2222-2222-2222-222222222203'::uuid)
) as g(id)
where p.category_id = '11111111-1111-1111-1111-111111111101' -- pizzas
   or p.id = '33333333-3333-3333-3333-333333333309'; -- buffalo chicken & feta special

insert into product_modifier_groups (product_id, modifier_group_id) values
  ('33333333-3333-3333-3333-333333333310', '22222222-2222-2222-2222-222222222203'), -- this week's special: remove only
  ('33333333-3333-3333-3333-333333333315', '22222222-2222-2222-2222-222222222205'); -- breakfast sandwich: optional extras

-- ---------------------------------------------------------------------------
-- Delivery zones & promo codes (delivery is disabled by default for this
-- trailer business — these seed rows exist so the feature can be switched on)
-- ---------------------------------------------------------------------------
insert into delivery_zones (postcode_prefixes, fee_minor, min_order_minor, free_delivery_threshold_minor, estimated_minutes) values
  ('{TS18}', 250, 1500, 3500, 35),
  ('{TS17,TS19}', 350, 1800, 4000, 40);

insert into promo_codes (code, type, value, min_basket_minor, active) values
  ('WELCOME10', 'percentage', 10, 1500, true),
  ('PICCOLO5', 'fixed', 500, 2500, true);
