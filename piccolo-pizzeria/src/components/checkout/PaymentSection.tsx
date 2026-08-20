"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Elements, ExpressCheckoutElement, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { AlertCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getStripe } from "@/lib/stripe-client";
import { formatMoney } from "@/lib/format";

/**
 * Apple Pay / Google Pay (and Link), rendered prominently above the card
 * form rather than buried as just another tab inside PaymentElement.
 * Renders nothing until Stripe reports a wallet is actually available on
 * this device/browser — onReady's availablePaymentMethods is undefined
 * when there's nothing to show, so there's no empty button row or a
 * dangling "or pay with card" divider on a desktop Chrome without a wallet
 * set up. Requires no server changes: the PaymentIntent's existing
 * automatic_payment_methods: { enabled: true } already covers wallets.
 */
function ExpressCheckout({ orderId, onError }: { orderId: string; onError: (message: string) => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [visible, setVisible] = useState(false);

  async function handleConfirm() {
    if (!stripe || !elements) return;

    const { error: confirmError } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/order-confirmation/${orderId}`,
      },
      redirect: "if_required",
    });

    if (confirmError) {
      onError(confirmError.message ?? "Payment failed. Please try again.");
      return;
    }

    router.push(`/order-confirmation/${orderId}`);
  }

  return (
    <div className={visible ? "mb-5" : "hidden"}>
      <ExpressCheckoutElement
        onReady={(event) => setVisible(Boolean(event.availablePaymentMethods))}
        onConfirm={handleConfirm}
        options={{ layout: { maxColumns: 2, maxRows: 1 } }}
      />
      <div className="mt-4 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-char-300">
        <div className="h-px flex-1 bg-char-200" />
        Or pay with card
        <div className="h-px flex-1 bg-char-200" />
      </div>
    </div>
  );
}

function PayButton({ orderId, totalMinor, error, setError }: { orderId: string; totalMinor: number; error: string | null; setError: (message: string | null) => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

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
  const [error, setError] = useState<string | null>(null);
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
      <ExpressCheckout orderId={orderId} onError={setError} />
      <PaymentElement options={{ layout: "tabs" }} />
      <PayButton orderId={orderId} totalMinor={totalMinor} error={error} setError={setError} />
    </Elements>
  );
}
