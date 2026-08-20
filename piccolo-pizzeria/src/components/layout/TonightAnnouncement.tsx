import { Sparkles } from "lucide-react";
import type { BusinessSettings } from "@/lib/types";

/** Storefront-wide banner. Renders nothing when inactive — no reserved space, no layout shift. */
export function TonightAnnouncement({ business }: { business: Pick<BusinessSettings, "announcementActive" | "announcementMessage"> }) {
  if (!business.announcementActive || !business.announcementMessage) return null;

  return (
    <div className="bg-char-900 px-4 py-2.5 text-center text-sm text-cream-50 sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-center gap-x-2 gap-y-0.5 sm:flex-row">
        <span className="flex items-center gap-1.5 font-semibold uppercase tracking-wide text-fire-400">
          <Sparkles className="h-3.5 w-3.5 shrink-0" />
          Tonight at Piccolo
        </span>
        <span className="hidden text-cream-100/80 sm:inline">·</span>
        <span className="text-cream-100">{business.announcementMessage}</span>
      </div>
    </div>
  );
}
