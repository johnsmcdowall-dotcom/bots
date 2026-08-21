import "server-only";
import type { OrderRecord } from "@/lib/types";

/**
 * Process-local order store used only when Supabase isn't configured, so
 * the full checkout → payment → confirmation → admin flow can be exercised
 * end-to-end in local/demo mode. This does NOT persist across serverless
 * invocations or server restarts — it exists purely so `npm run dev`
 * without a database still produces a working, testable app. Connect
 * Supabase for anything real.
 */
const globalForStore = globalThis as unknown as { __piccoloOrders?: Map<string, OrderRecord> };

export const memoryOrders: Map<string, OrderRecord> = globalForStore.__piccoloOrders ?? new Map();
globalForStore.__piccoloOrders = memoryOrders;

const globalForEvents = globalThis as unknown as { __piccoloWebhookEvents?: Set<string> };
export const memoryWebhookEvents: Set<string> = globalForEvents.__piccoloWebhookEvents ?? new Set();
globalForEvents.__piccoloWebhookEvents = memoryWebhookEvents;

/**
 * checkout idempotency key -> order id. Mirrors the `orders_idempotency_key_idx`
 * partial unique index used in the real database — see createPendingOrder,
 * which claims a key here synchronously (no `await` between the check and
 * the set) so two truly concurrent calls in the same process can never both
 * "win" the same key, exactly as the database's unique index guarantees for
 * the Supabase-backed branch.
 */
const globalForIdempotency = globalThis as unknown as { __piccoloIdempotencyKeys?: Map<string, string> };
export const memoryIdempotencyKeys: Map<string, string> = globalForIdempotency.__piccoloIdempotencyKeys ?? new Map();
globalForIdempotency.__piccoloIdempotencyKeys = memoryIdempotencyKeys;
