"use client";

import { ChevronsUpDownIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef } from "react";

import { confirmLeave } from "@/components/app/leave-guard";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
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
 * The header's church menu (S Flow C, F §4.1, §4.9 item 4): a radio list keyed
 * and selected by id, each row showing the role so same-name churches differ,
 * then a separator and "Join or create a church…", which pushes `/welcome`
 * (1b clarification 31), asking first while a settings page has unsaved
 * edits (`confirmLeave`, slice 6a-1; **Keep editing** returns focus to the
 * menu's trigger). A user with one church sees the same menu.
 */
export function ChurchSwitcher({ churches, activeId, onSelect }: Props) {
  const router = useRouter();
  const active = churches.find((c) => c.id === activeId) ?? null;
  const trigger = useRef<HTMLButtonElement>(null);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        ref={trigger}
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
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => confirmLeave(() => router.push("/welcome"), () => trigger.current)}>Join or create a church…</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
