"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-fire-500/10">
        <AlertTriangle className="h-6 w-6 text-fire-600" />
      </div>
      <h1 className="mt-6 font-display text-4xl uppercase tracking-tight text-char-900">Something Went Wrong</h1>
      <p className="mt-2 text-char-500">
        Sorry about that. Something went wrong on our end. Please try again, or head back to the
        menu.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button size="lg" onClick={() => reset()}>
          Try Again
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/menu">View Menu</Link>
        </Button>
      </div>
    </div>
  );
}
