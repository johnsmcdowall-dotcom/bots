"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { checkoutFormSchema, type CheckoutFormValues } from "@/lib/validations/checkout";
import type { OrderMethod } from "@/lib/types";

export function CheckoutForm({
  method,
  submitting,
  serverError,
  onSubmit,
}: {
  method: OrderMethod;
  submitting: boolean;
  serverError: string | null;
  onSubmit: (values: CheckoutFormValues) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CheckoutFormValues>({
    resolver: zodResolver(checkoutFormSchema),
    defaultValues: { firstName: "", lastName: "", phone: "", email: "", addressLine1: "", addressLine2: "", addressPostcode: "", notes: "" },
  });

  return (
    <form
      onSubmit={handleSubmit((values) => {
        if (method === "delivery" && (!values.addressLine1 || !values.addressPostcode)) {
          return;
        }
        onSubmit(values);
      })}
      className="space-y-6"
      noValidate
    >
      {serverError && (
        <div className="flex items-start gap-2 rounded-xl bg-fire-500/10 p-3 text-sm text-fire-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{serverError}</p>
        </div>
      )}

      <div>
        <h2 className="font-display text-lg text-char-900">Your Details</h2>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="firstName">First name</Label>
            <Input id="firstName" autoComplete="given-name" className="mt-1.5" {...register("firstName")} aria-invalid={!!errors.firstName} />
            {errors.firstName && <p className="mt-1 text-xs text-fire-600">{errors.firstName.message}</p>}
          </div>
          <div>
            <Label htmlFor="lastName">Last name</Label>
            <Input id="lastName" autoComplete="family-name" className="mt-1.5" {...register("lastName")} aria-invalid={!!errors.lastName} />
            {errors.lastName && <p className="mt-1 text-xs text-fire-600">{errors.lastName.message}</p>}
          </div>
        </div>
        <div className="mt-3">
          <Label htmlFor="phone">Mobile number</Label>
          <Input id="phone" type="tel" autoComplete="tel" inputMode="tel" className="mt-1.5" {...register("phone")} aria-invalid={!!errors.phone} />
          {errors.phone && <p className="mt-1 text-xs text-fire-600">{errors.phone.message}</p>}
        </div>
        <div className="mt-3">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" inputMode="email" className="mt-1.5" {...register("email")} aria-invalid={!!errors.email} />
          {errors.email && <p className="mt-1 text-xs text-fire-600">{errors.email.message}</p>}
        </div>
      </div>

      {method === "delivery" && (
        <div>
          <h2 className="font-display text-lg text-char-900">Delivery Address</h2>
          <div className="mt-3 space-y-3">
            <div>
              <Label htmlFor="addressLine1">Address</Label>
              <Input id="addressLine1" autoComplete="address-line1" className="mt-1.5" {...register("addressLine1")} />
            </div>
            <div>
              <Label htmlFor="addressLine2">Address line 2 (optional)</Label>
              <Input id="addressLine2" autoComplete="address-line2" className="mt-1.5" {...register("addressLine2")} />
            </div>
            <div>
              <Label htmlFor="addressPostcode">Postcode</Label>
              <Input id="addressPostcode" autoComplete="postal-code" className="mt-1.5 uppercase" {...register("addressPostcode")} />
            </div>
          </div>
        </div>
      )}

      <div>
        <Label htmlFor="notes">Order notes (optional)</Label>
        <Textarea id="notes" placeholder="Anything we should know?" className="mt-1.5" rows={2} {...register("notes")} />
      </div>

      <Button type="submit" size="xl" className="w-full" disabled={submitting}>
        {submitting ? "Please wait…" : "Continue to Payment"}
      </Button>
    </form>
  );
}
