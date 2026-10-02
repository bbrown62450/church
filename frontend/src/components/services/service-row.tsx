"use client";

import { EllipsisVerticalIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import type { ServiceSummary } from "@/lib/api/types";
import { formatSavedAt, formatServiceDate } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** A row's first line: the service date ("October 4, 2026"), else the stored date text, else "No date". */
export function serviceDateLabel(s: ServiceSummary): string {
  if (s.service_date_iso) return formatServiceDate(s.service_date_iso) || s.service_date_iso;
  return s.service_date.trim() || "No date";
}

/** A row's third line: who first saved it (it never changes) and when it was last saved. */
export function savedByLine(s: ServiceSummary): string {
  const at = formatSavedAt(s.saved_at);
  return s.created_by ? `Created by ${s.created_by.name} · last saved ${at}` : `Last saved ${at}`;
}

/** The row menu's name for screen readers: "More actions for {date}", plus the occasion when the service has no date, so undated rows differ. */
export function moreActionsLabel(s: ServiceSummary): string {
  const date = serviceDateLabel(s);
  const occasion = s.occasion.trim();
  return !s.service_date_iso && occasion !== "" ? `More actions for ${date}, ${occasion}` : `More actions for ${date}`;
}

/**
 * One saved service (slice 5a spec, "Services page" List): the date, the
 * occasion, who created it and when it was last saved, "Editing" when the
 * draft is this service. The row opens it ("Opening…" while it loads); the
 * menu beside it holds "Delete…". Both are 44 px tall.
 */
export function ServiceRow({
  service,
  editing,
  opening,
  disabled,
  onOpen,
  onDelete,
}: {
  service: ServiceSummary;
  editing: boolean;
  opening: boolean;
  disabled: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const date = serviceDateLabel(service);
  return (
    <li className="flex items-start gap-1 rounded-lg border">
      <button
        type="button"
        onClick={() => onOpen()}
        disabled={disabled}
        aria-busy={opening || undefined}
        className="grid min-h-11 min-w-0 flex-1 gap-0.5 rounded-lg p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
      >
        <span className="flex flex-wrap items-center gap-2 font-medium">
          {date}
          {editing ? <Badge variant="secondary">Editing</Badge> : null}
        </span>
        <span className="wrap-anywhere text-sm">{service.occasion.trim() || "No occasion"}</span>
        <span className="text-xs text-muted-foreground">{opening ? "Opening…" : savedByLine(service)}</span>
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={moreActionsLabel(service)}
          disabled={disabled}
          className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "m-1 size-11 shrink-0")}
        >
          <EllipsisVerticalIcon aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-36">
          <DropdownMenuItem variant="destructive" className="min-h-11 md:min-h-0" onClick={() => onDelete()}>
            Delete…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}
