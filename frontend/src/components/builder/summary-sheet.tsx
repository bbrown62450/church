"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { SummaryPanel } from "./summary-panel";

/**
 * The summary below `lg`, opened from the "Summary" button (S "Builder shell";
 * F §4.7, §4.9 item 6). Its height limit and rounded top are set here, so
 * `sheet.tsx` keeps the upstream shape (plan clarification 3).
 */
export function SummarySheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={(next) => onOpenChange(next)}>
      <SheetContent side="bottom" className="max-h-[85dvh] rounded-t-xl lg:hidden">
        <SheetHeader>
          <SheetTitle>Summary</SheetTitle>
        </SheetHeader>
        <div className="overflow-y-auto px-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <SummaryPanel onNavigate={() => onOpenChange(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
