"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { SETTINGS_SECTIONS } from "./sections";

/** The Settings area's section nav: a row of Material 3 chips on phones, a column of them beside the page from `md`. */
export function SettingsNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Settings sections">
      <ul className="flex flex-wrap gap-1 md:flex-col">
        {SETTINGS_SECTIONS.map((section) => {
          const current = pathname === section.href || pathname.startsWith(`${section.href}/`);
          return (
            <li key={section.href}>
              <Link
                href={section.href}
                aria-current={current ? "page" : undefined}
                className={cn(
                  "flex h-11 items-center rounded-full border border-border px-4 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-9 md:border-transparent",
                  "hover:bg-foreground/8 hover:text-foreground",
                  "aria-[current=page]:border-transparent aria-[current=page]:bg-secondary aria-[current=page]:text-secondary-foreground",
                )}
              >
                {section.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
