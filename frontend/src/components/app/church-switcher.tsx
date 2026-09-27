"use client";

import { ChevronsUpDownIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLabel, type Church } from "@/lib/church";
import { cn } from "@/lib/utils";

type Props = {
  churches: Church[];
  activeId: string | null;
  onSelect: (id: string) => void;
};

/**
 * The header's church menu (S Flow C, F §4.9 item 4): a radio list keyed and
 * selected by id, each row showing the role so same-name churches differ.
 * Slice 1b adds a separator and "Join or create a church…" below the group.
 */
export function ChurchSwitcher({ churches, activeId, onSelect }: Props) {
  const active = churches.find((c) => c.id === activeId) ?? null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={active ? `Active church: ${active.name}` : "Choose a church"}
        className={cn(
          buttonVariants({ variant: "ghost", size: "touch" }),
          "max-w-full justify-start px-2 font-semibold",
        )}
      >
        <span className="min-w-0 truncate">{active?.name ?? "Choose a church"}</span>
        <ChevronsUpDownIcon aria-hidden className="text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-auto min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Your churches</DropdownMenuLabel>
          <DropdownMenuRadioGroup
            value={activeId}
            onValueChange={(id: string) => onSelect(id)}
          >
            {churches.map((c) => (
              <DropdownMenuRadioItem key={c.id} value={c.id} label={c.name} closeOnClick>
                <span className="min-w-0 flex-1 truncate">{c.name}</span>{" "}
                <span className="text-xs text-muted-foreground">{roleLabel(c.role)}</span>
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
