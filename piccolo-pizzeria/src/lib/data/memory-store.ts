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
