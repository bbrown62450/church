import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type EmptyStateProps = {
  icon?: LucideIcon;
  /** One line. */
  title: string;
  /** One sentence. */
  description: string;
  /** The primary action, usually a size="touch" Button. */
  action?: ReactNode;
};

/** F §4.8 "Empty collection": icon, one-line title, one sentence, a primary action. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-10 text-center"
    >
      {Icon ? <Icon className="size-8 text-muted-foreground" aria-hidden="true" /> : null}
      <h2 className="text-base font-medium">{title}</h2>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
