"use client";

import { XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { SummaryPanel } from "./summary-panel";

/**
 * The summary below `lg`, opened from the "Summary" button (S "Builder shell";
 * F §4.7, §4.9 item 6). Its height limit and rounded top are set here, so
 * `sheet.tsx` keeps the upstream shape (plan clarification 3); so is its
 * Close button, a 44 px square in place of the upstream 28 px one (F §4.9).
 */
export function SummarySheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={(next) => onOpenChange(next)}>
      <SheetContent side="bottom" showCloseButton={false} className="max-h-[85dvh] rounded-t-xl lg:hidden">
        <SheetHeader>
          <SheetTitle>Summary</SheetTitle>
        </SheetHeader>
        <div className="overflow-y-auto px-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <SummaryPanel onNavigate={() => onOpenChange(false)} />
        </div>
        <SheetClose render={<Button variant="ghost" size="icon" className="absolute top-1.5 right-1.5 size-11" />}>
          <XIcon />
          <span className="sr-only">Close</span>
        </SheetClose>
      </SheetContent>
    </Sheet>
  );
}
