# Piccolo Pizzeria — Online Ordering Platform

A production-quality website and online ordering platform for Piccolo Pizzeria, an
independent wood-fired pizza trailer in the North East of England. Built with
Next.js (App Router), Supabase and Stripe.

This README assumes you're not a full-time developer — every step is spelled out.

---

## 1. What's here

- **Customer site** — home, menu, ordering (basket → collection/delivery →
  time slot → checkout → payment → confirmation), our story, find us,
  allergens, privacy/terms.
- **Admin dashboard** (`/admin`) — live order board, menu editor with
  one-click sold-out toggles, opening hours, business settings.
- **Demo mode** — with no environment variables set at all, the site runs
  fully off the seed data in `src/lib/seed-data.ts` and an in-process order
  store, so you can `npm run dev` and click through the entire ordering flow
  (including a simulated "payment") with zero setup. This is how you preview
  and tweak the design/menu before connecting real services.

### Tech stack

Next.js 16 (App Router, TypeScript), Tailwind CSS v4, Radix UI primitives,
React Hook Form + Zod, Zustand (basket), Supabase (Postgres + Auth +
Realtime), Stripe (Payment Element).

---

## 2. Local installation

You'll need [Node.js](https://nodejs.org) 20+ installed.

```bash
cd piccolo-pizzeria
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). That's it — this already
works in demo mode (see above). Sections 3–5 below connect the real backend.

---

## 3. Connecting Supabase (database, auth, realtime)

### 3.1 Create a project

1. Create a free account and project at [supabase.com](https://supabase.com).
2. In your project, go to **Project Settings → API** and copy:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon / public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (keep this secret —
     never put it in `NEXT_PUBLIC_*` or commit it)

Copy `.env.example` to `.env.local` and paste these three values in.

### 3.2 Apply the database schema

The schema lives in `supabase/migrations/*.sql`. Easiest path is the
[Supabase CLI](https://supabase.com/docs/guides/cli):

```bash
npm install -g supabase
supabase login
supabase link --project-ref <your-project-ref>   # found in the project URL
supabase db push                                  # applies the migrations
```

No CLI? Open **SQL Editor** in the Supabase dashboard and run the contents
of each file in `supabase/migrations/` in order (`0001_init.sql`,
`0002_rls.sql`, `0003_promo_usage.sql`).

### 3.3 Seed the real Piccolo menu

Run `supabase/seed.sql` the same way (CLI: `supabase db execute -f
supabase/seed.sql`, or paste it into the SQL Editor). It's safe to re-run —
it clears and re-inserts the menu tables each time. This loads the actual
Piccolo menu (pizzas, pizza sandwiches, specials, dips) with real prices —
edit it directly, or just use `/admin/menu` afterwards.

### 3.4 Create your first admin user

1. In the Supabase dashboard, go to **Authentication → Users → Add user**
   and create yourself an account (email + password).
2. Copy that user's UUID (shown in the users list).
3. In the **SQL Editor**, run:

   ```sql
   insert into profiles (id, role, full_name)
   values ('<paste-the-uuid-here>', 'admin', 'Your Name');
   ```

4. Sign in at `/admin/login`. To add kitchen staff later who shouldn't be
   able to change the menu or settings, give them `role = 'staff'` instead
   of `'admin'` — see `supabase/migrations/0002_rls.sql` for exactly what
   each role can do.

---

## 4. Connecting Stripe (payments)

1. Create a [Stripe](https://stripe.com) account. Use **test mode** while
   developing (toggle in the Stripe dashboard).
2. **Developers → API keys**: copy the publishable key into
   `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` and the secret key into
   `STRIPE_SECRET_KEY`.
3. Enable **Apple Pay / Google Pay** (optional but recommended) under
   **Settings → Payment methods** — the checkout already supports them via
   Stripe's Payment Element, nothing else to change in the code.

### Webhook (required for orders to actually confirm)

The webhook at `/api/webhooks/stripe` is what marks an order as paid — this
is the one thing checkout does not trust the browser for.

**Local development**, using the [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
stripe listen --forward-to localhost:3000/api/webhooks/stripe
```

It prints a `whsec_...` value — put that in `STRIPE_WEBHOOK_SECRET`.

**Production**: in the Stripe dashboard, **Developers → Webhooks → Add
endpoint**, URL `https://yourdomain.com/api/webhooks/stripe`, and subscribe
to `payment_intent.succeeded` and `payment_intent.payment_failed`. Copy the
signing secret it gives you into `STRIPE_WEBHOOK_SECRET` on your host.

Duplicate webhook deliveries (Stripe retries these) are handled safely — see
`webhook_events` in the schema and `hasProcessedWebhookEvent` in
`src/lib/data/orders.ts`.

---

## 5. Environment variables

See `.env.example` for the full list with comments. Summary:

| Variable | Required for | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Database, auth | |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Database, auth | Public, safe to expose |
| `SUPABASE_SERVICE_ROLE_KEY` | Orders, webhooks, admin | **Secret** — server-only |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Payments | Public |
| `STRIPE_SECRET_KEY` | Payments | **Secret** |
| `STRIPE_WEBHOOK_SECRET` | Payments | **Secret** |
| `RESEND_API_KEY` | Order emails | Optional — logs to console if unset |
| `NEXT_PUBLIC_GOOGLE_MAPS_EMBED_KEY` | Live map on Contact page | Public — optional, falls back to a location card if unset |
| `NEXT_PUBLIC_SITE_URL` | SEO metadata, Stripe redirect | Defaults to `localhost:3000` |

Never commit `.env.local` (it's already git-ignored).

---

## 6. Development commands

```bash
npm run dev      # start the dev server
npm run build    # production build (also runs the TypeScript check)
npm run start    # run a production build locally
npm run lint      # ESLint
```

---

## 7. Running the business day-to-day

- **Sold out an item right now**: `/admin/menu`, flip the switch next to the
  item. It's live immediately — the customer site checks availability
  server-side at the moment of ordering too, so a stale tab can't order
  something that just sold out.
- **Pause all ordering** (kitchen overwhelmed, closing early): `/admin/settings`
  → "Pause Ordering". Customers can still browse the menu, just can't order.
- **Change today's wait time**: `/admin/settings` → "Current wait" — this
  feeds directly into the collection time estimate shown at checkout.
- **Change opening hours / add a holiday closure**: `/admin/opening-hours`.
- **Add/edit/remove menu items**: `/admin/menu` → "Add Product" or the pencil
  icon on any item. Category, price, description, dietary tags, images
  (`placeholder:category:0`/`1`/`2` for the built-in art, or your own
  photo URL) all live here.
- **Live orders**: `/admin/orders` is a real-time board (new order sound/pop
  in without refreshing) — advance each order through
  Received → Accepted → Preparing → Ready → Completed.

---

## 8. Architecture notes (for developers)

- **Server-side price authority**: `src/lib/pricing.ts` recomputes every
  order's price from the database on the server — product prices,
  modifiers, sold-out flags, delivery fees and promo codes are never
  trusted from the browser. This runs at `/api/checkout/create-intent` and
  is what the Stripe PaymentIntent amount is actually built from.
- **Slot capacity**: `src/lib/slots.ts` + `/api/slots` compute time-slot
  availability from real booked-order counts, re-validated server-side again
  at order creation (`getBookedCounts` in `src/lib/data/orders.ts`) — a slot
  that fills up between page load and checkout is rejected, not silently
  overbooked.
- **Demo-mode fallback**: every function in `src/lib/data/*` tries Supabase
  first and falls back to `src/lib/seed-data.ts` (or an in-memory order
  store) if it's not configured or the query fails. This is why the site
  works with zero setup — see the comments in `src/lib/supabase/*` and
  `src/lib/data/orders.ts` for how that's wired.
- **Auth/RLS**: `supabase/migrations/0002_rls.sql` is deliberately strict —
  orders and promo codes have no public read policy at all; every write
  guest checkout needs goes through the service-role client server-side
  (`src/lib/supabase/admin.ts`), while `/admin` mutations use the signed-in
  user's own session so Postgres Row Level Security is the real
  authorization boundary, not just the UI. Every Server Action under
  `src/lib/actions/` re-checks the caller's role itself
  (`src/lib/actions/admin-auth.ts`) — Server Actions are POST endpoints
  reachable by anyone, not just from the admin UI.
- **Images**: products without real photography use a small set of
  hand-drawn placeholder SVGs (`public/images/placeholders`,
  `src/components/media/ProductImage.tsx`) generated to match the brand
  palette. Swap a product's `imageUrl` for a real photo path any time — no
  code changes needed. A handful of real trailer/food photos already live in
  `public/images/real`.

---

## 9. Deploying

Deploys cleanly to [Vercel](https://vercel.com) (or any Next.js host):

1. Push this repo to GitHub and import it in Vercel.
2. Add the environment variables from section 5 in the Vercel project
   settings.
3. Point the Stripe webhook (section 4) at your production URL.
4. Set `NEXT_PUBLIC_SITE_URL` to your real domain.

---

## 10. What's intentionally out of scope for v1

These are architected for (schema, types, abstractions all in place) but not
built out in the UI yet — flagged here rather than silently missing:

- Customer accounts / saved addresses / reorder (schema: `customers`,
  `addresses`; RLS already written).
- Drag-and-drop reordering of menu categories/products (use the numeric
  "Sort order" field in the product editor for now).
- Modifier group management UI in `/admin` (manage via Supabase Studio's
  table editor, or extend `src/lib/actions/menu.ts` — the pattern is
  established).
- A "resend confirmation email" action (the email itself already sends on
  payment — `src/lib/email.ts`).
