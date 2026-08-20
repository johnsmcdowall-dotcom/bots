"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { AlertCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getStripe } from "@/lib/stripe-client";
import { formatMoney } from "@/lib/format";

function PayButton({ orderId, totalMinor }: { orderId: string; totalMinor: number }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePay() {
    if (!stripe || !elements) return;
    setSubmitting(true);
    setError(null);

    const { error: submitError } = await elements.submit();
    if (submitError) {
      setError(submitError.message ?? "Please check your payment details.");
      setSubmitting(false);
      return;
    }

    const { error: confirmError } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/order-confirmation/${orderId}`,
      },
      redirect: "if_required",
    });

    if (confirmError) {
      setError(confirmError.message ?? "Payment failed. Please try again.");
      setSubmitting(false);
      return;
    }

    router.push(`/order-confirmation/${orderId}`);
  }

  return (
    <div className="mt-6">
      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl bg-fire-500/10 p-3 text-sm text-fire-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      <Button size="xl" variant="accent" className="w-full" onClick={handlePay} disabled={!stripe || submitting}>
        {submitting ? "Processing…" : `Pay ${formatMoney(totalMinor)}`}
      </Button>
      <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-char-400">
        <Lock className="h-3 w-3" /> Payments are securely processed by Stripe. We never see your card details.
      </p>
    </div>
  );
}

export function PaymentSection({ clientSecret, orderId, totalMinor }: { clientSecret: string; orderId: string; totalMinor: number }) {
  const stripePromise = getStripe();
  if (!stripePromise) return null;

  return (
    <Elements
      stripe={stripePromise}
      options={{
        clientSecret,
        appearance: {
          theme: "stripe",
          variables: {
            colorPrimary: "#b73a2a",
            colorBackground: "#faf5ea",
            colorText: "#0b0b0b",
            fontFamily: "var(--font-sans), sans-serif",
            borderRadius: "12px",
          },
        },
      }}
    >
      <PaymentElement options={{ layout: "tabs" }} />
      <PayButton orderId={orderId} totalMinor={totalMinor} />
    </Elements>
  );
}
