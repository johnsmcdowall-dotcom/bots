import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LogoMark } from "@/components/brand/LogoMark";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-4 text-center">
      <div className="w-24">
        <LogoMark />
      </div>
      <h1 className="mt-6 font-display text-4xl uppercase tracking-tight text-char-900">Page Not Found</h1>
      <p className="mt-2 text-char-500">
        We couldn&apos;t find what you were looking for. It might have moved, or the link might be
        out of date.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button asChild size="lg">
          <Link href="/">Back to Home</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/menu">View Menu</Link>
        </Button>
      </div>
    </div>
  );
}
