import { z } from "zod";

export const cartLineSchema = z.object({
  productId: z.string().min(1),
  quantity: z.number().int().min(1).max(20),
  modifierOptionIds: z.array(z.string()).max(30),
  notes: z.string().max(280).optional(),
});

export const customerSchema = z.object({
  firstName: z.string().trim().min(1, "First name is required").max(60),
  lastName: z.string().trim().min(1, "Last name is required").max(60),
  phone: z
    .string()
    .trim()
    .min(7, "Enter a valid phone number")
    .max(20)
    .regex(/^[0-9+()\s-]+$/, "Enter a valid phone number"),
  email: z.string().trim().email("Enter a valid email address"),
});

export const addressSchema = z.object({
  line1: z.string().trim().min(1, "Address is required").max(120),
  line2: z.string().trim().max(120).optional(),
  postcode: z
    .string()
    .trim()
    .min(5, "Enter a valid UK postcode")
    .max(9)
    .regex(/^[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}$/, "Enter a valid UK postcode"),
});

export const checkoutRequestSchema = z
  .object({
    lines: z.array(cartLineSchema).min(1, "Your basket is empty"),
    method: z.enum(["collection", "delivery"]),
    timing: z.enum(["asap", "scheduled"]),
    scheduledDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
    scheduledTime: z.string().regex(/^\d{2}:\d{2}$/).optional(),
    promoCode: z.string().trim().max(40).optional(),
    customer: customerSchema,
    address: addressSchema.optional(),
    notes: z.string().max(280).optional(),
    // Stable per-checkout-attempt id, generated once client-side and
    // persisted alongside the basket so it survives a page refresh. Lets
    // the server recognise "this exact attempt already happened" instead of
    // creating a new order every time this endpoint is hit.
    idempotencyKey: z.string().uuid("Invalid checkout session"),
  })
  .superRefine((val, ctx) => {
    if (val.method === "delivery" && !val.address) {
      ctx.addIssue({ code: "custom", message: "Delivery address is required", path: ["address"] });
    }
    if (val.timing === "scheduled" && (!val.scheduledDate || !val.scheduledTime)) {
      ctx.addIssue({ code: "custom", message: "Choose a collection/delivery time", path: ["scheduledTime"] });
    }
  });

export type CheckoutRequest = z.infer<typeof checkoutRequestSchema>;

// Client-side form schema (customer + address only — basket/timing come from the store).
export const checkoutFormSchema = z.object({
  firstName: customerSchema.shape.firstName,
  lastName: customerSchema.shape.lastName,
  phone: customerSchema.shape.phone,
  email: customerSchema.shape.email,
  addressLine1: z.string().trim().max(120).optional(),
  addressLine2: z.string().trim().max(120).optional(),
  addressPostcode: z.string().trim().max(9).optional(),
  notes: z.string().max(280).optional(),
});

export type CheckoutFormValues = z.infer<typeof checkoutFormSchema>;
