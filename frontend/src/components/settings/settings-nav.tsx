"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { SETTINGS_SECTIONS } from "./sections";

/** The Settings area's section nav: a row of links on phones, a column beside the page from `md`. */
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
                  "flex h-11 items-center rounded-md px-3 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-9",
                  "hover:text-foreground aria-[current=page]:bg-muted aria-[current=page]:text-foreground",
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
