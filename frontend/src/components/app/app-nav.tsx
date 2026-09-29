"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

/** Nav items in order; each appears once its slice ships (F §4.2). 5a adds "Services", 5b or 6a "Settings". */
export const NAV_ITEMS = [{ href: "/builder", label: "Builder" }] as const;

/**
 * Primary navigation (F §4.2; S Hand-offs "AppNav"). One element for every
 * width: `AppHeader` places it as a segmented row under the header below
 * `md`, and as a link row inside the header from `md`.
 */
export function AppNav({ className }: { className?: string }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className={className}>
      <ul className="grid auto-cols-fr grid-flow-col gap-1 rounded-lg bg-muted p-1 md:flex md:bg-transparent md:p-0">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-9 items-center justify-center rounded-md px-3 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  "aria-[current=page]:bg-background aria-[current=page]:text-foreground aria-[current=page]:shadow-sm",
                  "md:aria-[current=page]:bg-muted md:aria-[current=page]:shadow-none",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
