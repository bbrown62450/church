import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type PageHeaderProps = {
  title: string;
  description?: string;
  /** More classes for the description (`[overflow-wrap:anywhere]` when it holds a name that may not break; slice 6b-2b). */
  descriptionClassName?: string;
  actions?: ReactNode;
};

/** The page's h1, an optional one-line description and the page actions (stacked on phones). */
export function PageHeader({ title, description, descriptionClassName, actions }: PageHeaderProps) {
  return (
    <div data-slot="page-header" className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className={cn("mt-1 text-sm text-muted-foreground", descriptionClassName)}>{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
