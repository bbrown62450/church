"use client";

import { EllipsisVerticalIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { NewServiceMenuItem } from "./new-service-menu-item";

/** "Service Builder", the "Summary" button (below `lg`) and the overflow menu (S "Builder shell"). */
export function StepHeader({ onOpenSummary, onNewService }: { onOpenSummary: () => void; onNewService: () => void }) {
  return (
    <div className="flex items-center gap-2 pt-4 pb-2">
      <h1 className="min-w-0 flex-1 text-xl font-semibold tracking-tight">Service Builder</h1>
      <button
        type="button"
        onClick={() => onOpenSummary()}
        className={cn(buttonVariants({ variant: "outline", size: "touch" }), "lg:hidden")}
      >
        Summary
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="More actions"
          className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11")}
        >
          <EllipsisVerticalIcon aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-44">
          <NewServiceMenuItem onSelect={onNewService} />
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
