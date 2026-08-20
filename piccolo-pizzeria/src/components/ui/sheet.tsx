"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const Sheet = Dialog.Root;
const SheetTrigger = Dialog.Trigger;
const SheetClose = Dialog.Close;

/**
 * Bottom sheet on mobile, side/center panel on larger screens — the shared
 * shell behind ProductModal and BasketDrawer. `side` controls the desktop
 * anchor; on mobile it always slides up from the bottom for thumb reach.
 */
function SheetContent({
  className,
  children,
  side = "bottom",
  showClose = true,
  ...props
}: React.ComponentPropsWithoutRef<typeof Dialog.Content> & {
  side?: "bottom" | "right";
  showClose?: boolean;
}) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-char-900/60 backdrop-blur-[2px] data-[state=open]:animate-fade-in" />
      <Dialog.Content
        className={cn(
          "fixed z-50 flex flex-col bg-cream-50 shadow-2xl outline-none",
          "inset-x-0 bottom-0 max-h-[92dvh] rounded-t-3xl",
          "data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom data-[state=closed]:animate-out data-[state=closed]:slide-out-to-bottom data-[state=closed]:duration-200 data-[state=open]:duration-300",
          side === "right" &&
            "sm:inset-y-0 sm:right-0 sm:left-auto sm:bottom-auto sm:h-full sm:max-h-full sm:w-full sm:max-w-md sm:rounded-t-none sm:rounded-l-3xl sm:data-[state=open]:slide-in-from-right sm:data-[state=closed]:slide-out-to-right",
          side === "bottom" && "sm:inset-x-0 sm:bottom-0 sm:mx-auto sm:max-w-2xl sm:rounded-3xl sm:mb-6",
          className
        )}
        {...props}
      >
        <div className="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-char-200 sm:hidden" aria-hidden />
        {children}
        {showClose && (
          <Dialog.Close
            className="absolute right-4 top-4 rounded-full bg-cream-100/90 p-2 text-char-700 shadow-sm transition hover:bg-cream-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fire-500"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Dialog.Close>
        )}
      </Dialog.Content>
    </Dialog.Portal>
  );
}

function SheetHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 pt-4 sm:px-6", className)} {...props} />;
}

function SheetTitle({ className, ...props }: React.ComponentPropsWithoutRef<typeof Dialog.Title>) {
  return <Dialog.Title className={cn("font-display text-2xl uppercase tracking-tight text-char-900", className)} {...props} />;
}

function SheetDescription({ className, ...props }: React.ComponentPropsWithoutRef<typeof Dialog.Description>) {
  return <Dialog.Description className={cn("text-sm text-char-500", className)} {...props} />;
}

export { Sheet, SheetTrigger, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetDescription };
