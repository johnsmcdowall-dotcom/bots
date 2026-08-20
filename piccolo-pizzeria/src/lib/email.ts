import "server-only";
import type { OrderRecord } from "@/lib/types";
import { formatMoney, formatOrderDateTime } from "@/lib/format";

/**
 * Minimal transactional email abstraction over the Resend HTTP API — no SDK
 * dependency, just a fetch call. Swap the implementation here if you'd
 * rather use another provider; nothing else in the app needs to change.
 * No-ops (with a console notice) when RESEND_API_KEY isn't set, so the rest
 * of the app works without an email provider configured.
 */
export async function sendEmail(input: { to: string; subject: string; html: string }): Promise<void> {
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.RESEND_FROM_EMAIL || "Piccolo Pizzeria <orders@piccolopizzeria.co.uk>";

  if (!apiKey) {
    console.info(`[email:skipped, no RESEND_API_KEY] to=${input.to} subject="${input.subject}"`);
    return;
  }

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from, to: input.to, subject: input.subject, html: input.html }),
    });
    if (!res.ok) {
      console.error(`[email:failed] ${res.status} ${await res.text()}`);
    }
  } catch (err) {
    console.error("[email:error]", err);
  }
}

export async function sendOrderReceivedEmail(order: OrderRecord): Promise<void> {
  const itemsHtml = order.items
    .map((item) => `<li>${item.quantity}× ${item.name}${item.modifiers.length ? ` — ${item.modifiers.map((m) => m.optionName).join(", ")}` : ""}</li>`)
    .join("");

  await sendEmail({
    to: order.customer.email,
    subject: `Order #${order.orderNumber} received — Piccolo Pizzeria`,
    html: `
      <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
        <h1 style="font-size: 20px;">Thanks ${order.customer.firstName} — we've got your order</h1>
        <p>Order <strong>#${order.orderNumber}</strong></p>
        <p>${order.method === "delivery" ? "Delivery" : "Collection"}: <strong>${formatOrderDateTime(order.requestedTime)}</strong></p>
        <ul>${itemsHtml}</ul>
        <p style="font-size: 18px; font-weight: bold;">Total: ${formatMoney(order.totalMinor)}</p>
      </div>
    `,
  });
}
